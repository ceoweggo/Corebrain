"""
Componentes para manejo y análisis de consultas.
"""
import os
import json
import time
import re
import sqlite3
import pickle
import hashlib

from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
from pathlib import Path

from corebrain.cli.utils import print_colored

class QueryCache:
    """Sistema de caché multinivel para consultas."""
    
    def __init__(self, cache_dir: str = None, ttl: int = 86400, memory_limit: int = 100):
        """
        Inicializa el sistema de caché.
        
        Args:
            cache_dir: Directorio para el caché persistente
            ttl: Tiempo de vida del caché en segundos (default: 24 horas)
            memory_limit: Límite de entradas en caché de memoria
        """
        # Caché en memoria (más rápido, pero volátil)
        self.memory_cache = {}
        self.memory_timestamps = {}
        self.memory_limit = memory_limit
        self.memory_lru = []  # Lista para seguimiento de menos usados recientemente
        
        # Caché persistente (más lento, pero permanente)
        self.ttl = ttl
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".corebrain_cache"
            
        # Crear directorio de caché si no existe
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar base de datos SQLite para metadatos
        self.db_path = self.cache_dir / "cache_metadata.db"
        self._init_db()
        
        print_colored(f"Caché inicializado en {self.cache_dir}", "blue")
    
    def _init_db(self):
        """Inicializa la base de datos SQLite para metadatos de caché."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Crear tabla de metadatos si no existe
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache_metadata (
            query_hash TEXT PRIMARY KEY,
            query TEXT,
            config_id TEXT,
            created_at TIMESTAMP,
            last_accessed TIMESTAMP,
            hit_count INTEGER DEFAULT 1
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_hash(self, query: str, config_id: str, collection_name: Optional[str] = None) -> str:
        """Genera un hash único para la consulta."""
        # Normalizar la consulta (eliminar espacios extra, convertir a minúsculas)
        normalized_query = re.sub(r'\s+', ' ', query.lower().strip())
        
        # Crear string compuesto para el hash
        hash_input = f"{normalized_query}|{config_id}"
        if collection_name:
            hash_input += f"|{collection_name}"
            
        # Generar el hash
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _get_cache_path(self, query_hash: str) -> Path:
        """Obtiene la ruta del archivo de caché para un hash dado."""
        # Usar los primeros caracteres del hash para crear subdirectorios
        # Esto evita tener demasiados archivos en un solo directorio
        subdir = query_hash[:2]
        cache_subdir = self.cache_dir / subdir
        cache_subdir.mkdir(exist_ok=True)
        
        return cache_subdir / f"{query_hash}.cache"
    
    def _update_metadata(self, query_hash: str, query: str, config_id: str):
        """Actualiza los metadatos en la base de datos."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Verificar si el hash ya existe
        cursor.execute("SELECT hit_count FROM cache_metadata WHERE query_hash = ?", (query_hash,))
        result = cursor.fetchone()
        
        if result:
            # Actualizar entrada existente
            hit_count = result[0] + 1
            cursor.execute('''
            UPDATE cache_metadata 
            SET last_accessed = ?, hit_count = ? 
            WHERE query_hash = ?
            ''', (now, hit_count, query_hash))
        else:
            # Insertar nueva entrada
            cursor.execute('''
            INSERT INTO cache_metadata (query_hash, query, config_id, created_at, last_accessed, hit_count)
            VALUES (?, ?, ?, ?, ?, 1)
            ''', (query_hash, query, config_id, now, now))
        
        conn.commit()
        conn.close()
    
    def _update_memory_lru(self, query_hash: str):
        """Actualiza la lista LRU (Least Recently Used) para el caché en memoria."""
        if query_hash in self.memory_lru:
            # Mover al final (más recientemente usado)
            self.memory_lru.remove(query_hash)
        
        self.memory_lru.append(query_hash)
        
        # Si excedemos el límite, eliminar el elemento menos usado recientemente
        if len(self.memory_lru) > self.memory_limit:
            oldest_hash = self.memory_lru.pop(0)
            if oldest_hash in self.memory_cache:
                del self.memory_cache[oldest_hash]
                del self.memory_timestamps[oldest_hash]
    
    def get(self, query: str, config_id: str, collection_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Obtiene un resultado cacheado si existe y no ha expirado.
        
        Args:
            query: Consulta en lenguaje natural
            config_id: ID de configuración de la base de datos
            collection_name: Nombre de la colección/tabla (opcional)
            
        Returns:
            Resultado cacheado o None si no existe o ha expirado
        """
        query_hash = self._get_hash(query, config_id, collection_name)
        
        # 1. Verificar caché en memoria (más rápido)
        if query_hash in self.memory_cache:
            timestamp = self.memory_timestamps[query_hash]
            if (time.time() - timestamp) < self.ttl:
                self._update_memory_lru(query_hash)
                self._update_metadata(query_hash, query, config_id)
                print_colored(f"Cache hit (memory): {query[:30]}...", "green")
                return self.memory_cache[query_hash]
            else:
                # Expirado en memoria
                del self.memory_cache[query_hash]
                del self.memory_timestamps[query_hash]
                if query_hash in self.memory_lru:
                    self.memory_lru.remove(query_hash)
        
        # 2. Verificar caché en disco
        cache_path = self._get_cache_path(query_hash)
        if cache_path.exists():
            # Verificar edad del archivo
            file_age = time.time() - cache_path.stat().st_mtime
            if file_age < self.ttl:
                try:
                    with open(cache_path, 'rb') as f:
                        result = pickle.load(f)
                    
                    # Guardar también en caché de memoria
                    self.memory_cache[query_hash] = result
                    self.memory_timestamps[query_hash] = time.time()
                    self._update_memory_lru(query_hash)
                    self._update_metadata(query_hash, query, config_id)
                    
                    print_colored(f"Cache hit (disk): {query[:30]}...", "green")
                    return result
                except Exception as e:
                    print_colored(f"Error al cargar caché: {str(e)}", "red")
                    # Si hay error al cargar, eliminar el archivo corrupto
                    cache_path.unlink(missing_ok=True)
            else:
                # Archivo expirado, eliminarlo
                cache_path.unlink(missing_ok=True)
        
        return None
    
    def set(self, query: str, config_id: str, result: Dict[str, Any], collection_name: Optional[str] = None):
        """
        Guarda un resultado en el caché.
        
        Args:
            query: Consulta en lenguaje natural
            config_id: ID de configuración
            result: Resultado a cachear
            collection_name: Nombre de la colección/tabla (opcional)
        """
        query_hash = self._get_hash(query, config_id, collection_name)
        
        # 1. Guardar en caché de memoria
        self.memory_cache[query_hash] = result
        self.memory_timestamps[query_hash] = time.time()
        self._update_memory_lru(query_hash)
        
        # 2. Guardar en caché persistente
        try:
            cache_path = self._get_cache_path(query_hash)
            with open(cache_path, 'wb') as f:
                pickle.dump(result, f)
            
            # 3. Actualizar metadatos
            self._update_metadata(query_hash, query, config_id)
            
            print_colored(f"Cached: {query[:30]}...", "green")
        except Exception as e:
            print_colored(f"Error al guardar en caché: {str(e)}", "red")
    
    def clear(self, older_than: int = None):
        """
        Limpia el caché.
        
        Args:
            older_than: Limpiar solo entradas más antiguas que esta cantidad de segundos
        """
        # Limpiar caché en memoria
        if older_than:
            current_time = time.time()
            keys_to_remove = [
                k for k, timestamp in self.memory_timestamps.items()
                if (current_time - timestamp) > older_than
            ]
            
            for k in keys_to_remove:
                if k in self.memory_cache:
                    del self.memory_cache[k]
                if k in self.memory_timestamps:
                    del self.memory_timestamps[k]
                if k in self.memory_lru:
                    self.memory_lru.remove(k)
        else:
            self.memory_cache.clear()
            self.memory_timestamps.clear()
            self.memory_lru.clear()
        
        # Limpiar caché en disco
        if older_than:
            cutoff_time = time.time() - older_than
            
            # Usar la base de datos para encontrar archivos antiguos
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Convertir cutoff_time a formato ISO
            cutoff_datetime = datetime.fromtimestamp(cutoff_time).isoformat()
            
            cursor.execute(
                "SELECT query_hash FROM cache_metadata WHERE last_accessed < ?",
                (cutoff_datetime,)
            )
            
            old_hashes = [row[0] for row in cursor.fetchall()]
            
            # Eliminar archivos antiguos
            for query_hash in old_hashes:
                cache_path = self._get_cache_path(query_hash)
                if cache_path.exists():
                    cache_path.unlink()
                
                # Eliminar de la base de datos
                cursor.execute(
                    "DELETE FROM cache_metadata WHERE query_hash = ?",
                    (query_hash,)
                )
            
            conn.commit()
            conn.close()
        else:
            # Eliminar todos los archivos de caché
            for subdir in self.cache_dir.iterdir():
                if subdir.is_dir():
                    for cache_file in subdir.glob("*.cache"):
                        cache_file.unlink()
            
            # Reiniciar la base de datos
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache_metadata")
            conn.commit()
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché."""
        # Contar archivos en disco
        disk_count = 0
        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                disk_count += len(list(subdir.glob("*.cache")))
        
        # Obtener estadísticas de la base de datos
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Total de entradas
        cursor.execute("SELECT COUNT(*) FROM cache_metadata")
        total_entries = cursor.fetchone()[0]
        
        # Consultas más frecuentes
        cursor.execute(
            "SELECT query, hit_count FROM cache_metadata ORDER BY hit_count DESC LIMIT 5"
        )
        top_queries = cursor.fetchall()
        
        # Edad promedio
        cursor.execute(
            "SELECT AVG(strftime('%s', 'now') - strftime('%s', created_at)) FROM cache_metadata"
        )
        avg_age = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "memory_cache_size": len(self.memory_cache),
            "disk_cache_size": disk_count,
            "total_entries": total_entries,
            "top_queries": top_queries,
            "average_age_seconds": avg_age,
            "cache_directory": str(self.cache_dir)
        }

class QueryTemplate:
    """Plantilla de consulta predefinida para patrones comunes."""
    
    def __init__(self, pattern: str, description: str, 
                 sql_template: Optional[str] = None,
                 generator_func: Optional[Callable] = None,
                 db_type: str = "sql",
                 applicable_tables: Optional[List[str]] = None):
        """
        Inicializa una plantilla de consulta.
        
        Args:
            pattern: Patrón de lenguaje natural que coincide con esta plantilla
            description: Descripción de la plantilla
            sql_template: Plantilla SQL con marcadores para parámetros
            generator_func: Función alternativa para generar la consulta
            db_type: Tipo de base de datos (sql, mongodb)
            applicable_tables: Lista de tablas a las que aplica esta plantilla
        """
        self.pattern = pattern
        self.description = description
        self.sql_template = sql_template
        self.generator_func = generator_func
        self.db_type = db_type
        self.applicable_tables = applicable_tables or []
        
        # Compilar expresión regular para el patrón
        self.regex = self._compile_pattern(pattern)
    
    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """Compila el patrón en una expresión regular."""
        # Reemplazar marcadores especiales con grupos de captura
        regex_pattern = pattern
        
        # {table} se convierte en grupo de captura para el nombre de tabla
        regex_pattern = regex_pattern.replace("{table}", r"(\w+)")
        
        # {field} se convierte en grupo de captura para el nombre de campo
        regex_pattern = regex_pattern.replace("{field}", r"(\w+)")
        
        # {value} se convierte en grupo de captura para un valor
        regex_pattern = regex_pattern.replace("{value}", r"([^,.\s]+)")
        
        # {number} se convierte en grupo de captura para un número
        regex_pattern = regex_pattern.replace("{number}", r"(\d+)")
        
        # Hacer coincidir el patrón completo
        regex_pattern = f"^{regex_pattern}$"
        
        return re.compile(regex_pattern, re.IGNORECASE)
    
    def matches(self, query: str) -> Tuple[bool, List[str]]:
        """
        Verifica si una consulta coincide con esta plantilla.
        
        Args:
            query: Consulta a verificar
            
        Returns:
            Tupla de (coincide, [parámetros capturados])
        """
        match = self.regex.match(query)
        if match:
            return True, list(match.groups())
        return False, []
    
    def generate_query(self, params: List[str], db_schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Genera una consulta a partir de los parámetros capturados.
        
        Args:
            params: Parámetros capturados del patrón
            db_schema: Esquema de la base de datos
            
        Returns:
            Consulta generada o None si no se puede generar
        """
        if self.generator_func:
            # Usar función personalizada
            return self.generator_func(params, db_schema)
        
        if not self.sql_template:
            return None
            
        # Intentar aplicar la plantilla SQL con los parámetros
        try:
            sql_query = self.sql_template
            
            # Reemplazar parámetros en la plantilla
            for i, param in enumerate(params):
                placeholder = f"${i+1}"
                sql_query = sql_query.replace(placeholder, param)
            
            # Verificar si hay algún parámetro sin reemplazar
            if "$" in sql_query:
                return None
                
            return {"sql": sql_query}
        except Exception:
            return None

class QueryAnalyzer:
    """Analiza patrones de consultas para sugerir optimizaciones."""
    
    def __init__(self, query_log_path: str = None, template_path: str = None):
        """
        Inicializa el analizador de consultas.
        
        Args:
            query_log_path: Ruta al archivo de registro de consultas
            template_path: Ruta al archivo de plantillas
        """
        self.query_log_path = query_log_path or os.path.join(
            Path.home(), ".corebrain_cache", "query_log.db"
        )
        
        self.template_path = template_path or os.path.join(
            Path.home(), ".corebrain_cache", "templates.json"
        )
        
        # Inicializar base de datos
        self._init_db()
        
        # Plantillas predefinidas para consultas comunes
        self.templates = self._load_default_templates()
        
        # Cargar plantillas personalizadas
        self._load_custom_templates()
        
        # Plantillas comunes para identificar patrones
        self.common_patterns = [
            r"muestra\s+(?:todos\s+)?los\s+(\w+)",
            r"lista\s+(?:de\s+)?(?:todos\s+)?los\s+(\w+)",
            r"busca\s+(\w+)\s+donde",
            r"cu[aá]ntos\s+(\w+)\s+hay",
            r"total\s+de\s+(\w+)"
        ]
    
    def _init_db(self):
        """Inicializa la base de datos para el registro de consultas."""
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(self.query_log_path), exist_ok=True)
        
        conn = sqlite3.connect(self.query_log_path)
        cursor = conn.cursor()
        
        # Crear tabla de registro si no existe
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS query_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            config_id TEXT,
            collection_name TEXT,
            timestamp TIMESTAMP,
            execution_time REAL,
            cost REAL,
            result_count INTEGER,
            pattern TEXT
        )
        ''')
        
        # Crear tabla de patrones detectados
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS query_patterns (
            pattern TEXT PRIMARY KEY,
            count INTEGER,
            avg_execution_time REAL,
            avg_cost REAL,
            last_updated TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_default_templates(self) -> List[QueryTemplate]:
        """Carga las plantillas predefinidas para consultas comunes."""
        templates = []
        
        # Listar todos los registros de una tabla
        templates.append(
            QueryTemplate(
                pattern="muestra todos los {table}",
                description="Listar todos los registros de una tabla",
                sql_template="SELECT * FROM $1 LIMIT 100",
                db_type="sql"
            )
        )
        
        # Contar registros
        templates.append(
            QueryTemplate(
                pattern="cuántos {table} hay",
                description="Contar registros en una tabla",
                sql_template="SELECT COUNT(*) FROM $1",
                db_type="sql"
            )
        )
        
        # Buscar por ID
        templates.append(
            QueryTemplate(
                pattern="busca el {table} con id {value}",
                description="Buscar registro por ID",
                sql_template="SELECT * FROM $1 WHERE id = $2",
                db_type="sql"
            )
        )
        
         # Listar ordenados
        templates.append(
            QueryTemplate(
                pattern="lista los {table} ordenados por {field}",
                description="Listar registros ordenados por campo",
                sql_template="SELECT * FROM $1 ORDER BY $2 LIMIT 100",
                db_type="sql"
            )
        )
        
        # Buscar por email
        templates.append(
            QueryTemplate(
                pattern="busca el usuario con email {value}",
                description="Buscar usuario por email",
                sql_template="SELECT * FROM users WHERE email = '$2'",
                db_type="sql"
            )
        )
        
        # Contar por campo
        templates.append(
            QueryTemplate(
                pattern="cuántos {table} hay por {field}",
                description="Contar registros agrupados por campo",
                sql_template="SELECT $2, COUNT(*) FROM $1 GROUP BY $2",
                db_type="sql"
            )
        )
        
        # Contar usuarios activos
        templates.append(
            QueryTemplate(
                pattern="cuántos usuarios activos hay",
                description="Contar usuarios activos",
                sql_template="SELECT COUNT(*) FROM users WHERE is_active = TRUE",
                db_type="sql",
                applicable_tables=["users"]
            )
        )
        
        # Listar usuarios por fecha de registro
        templates.append(
            QueryTemplate(
                pattern="usuarios registrados en los últimos {number} días",
                description="Listar usuarios recientes",
                sql_template="""
                SELECT * FROM users 
                WHERE created_at >= datetime('now', '-$2 days')
                ORDER BY created_at DESC
                LIMIT 100
                """,
                db_type="sql",
                applicable_tables=["users"]
            )
        )
        
        # Buscar empresas
        templates.append(
            QueryTemplate(
                pattern="usuarios que tienen empresa",
                description="Buscar usuarios con empresa asignada",
                sql_template="""
                SELECT u.* FROM users u
                INNER JOIN businesses b ON u.id = b.owner_id
                WHERE u.is_business = TRUE
                LIMIT 100
                """,
                db_type="sql",
                applicable_tables=["users", "businesses"]
            )
        )
        
        # Buscar negocios
        templates.append(
            QueryTemplate(
                pattern="busca negocios en {value}",
                description="Buscar negocios por ubicación",
                sql_template="""
                SELECT * FROM businesses 
                WHERE address_city LIKE '%$2%' OR address_province LIKE '%$2%'
                LIMIT 100
                """,
                db_type="sql",
                applicable_tables=["businesses"]
            )
        )
        
        # MongoDB: Listar documentos
        templates.append(
            QueryTemplate(
                pattern="muestra todos los documentos de {table}",
                description="Listar documentos en una colección",
                db_type="mongodb",
                generator_func=lambda params, schema: {
                    "collection": params[0],
                    "operation": "find",
                    "query": {},
                    "limit": 100
                }
            )
        )
        
        return templates
    
    def _load_custom_templates(self):
        """Carga plantillas personalizadas desde el archivo."""
        if not os.path.exists(self.template_path):
            return
            
        try:
            with open(self.template_path, 'r') as f:
                custom_templates = json.load(f)
                
            for template_data in custom_templates:
                # Crear plantilla desde datos JSON
                template = QueryTemplate(
                    pattern=template_data.get("pattern", ""),
                    description=template_data.get("description", ""),
                    sql_template=template_data.get("sql_template"),
                    db_type=template_data.get("db_type", "sql"),
                    applicable_tables=template_data.get("applicable_tables", [])
                )
                
                self.templates.append(template)
                
        except Exception as e:
            print_colored(f"Error al cargar plantillas personalizadas: {str(e)}", "red")
    
    def save_custom_template(self, template: QueryTemplate) -> bool:
        """
        Guarda una plantilla personalizada.
        
        Args:
            template: Plantilla a guardar
            
        Returns:
            True si se guardó correctamente
        """
        # Cargar plantillas existentes
        custom_templates = []
        if os.path.exists(self.template_path):
            try:
                with open(self.template_path, 'r') as f:
                    custom_templates = json.load(f)
            except:
                custom_templates = []
        
        # Convertir plantilla a diccionario
        template_data = {
            "pattern": template.pattern,
            "description": template.description,
            "sql_template": template.sql_template,
            "db_type": template.db_type,
            "applicable_tables": template.applicable_tables
        }
        
        # Verificar si ya existe una plantilla con el mismo patrón
        for i, existing in enumerate(custom_templates):
            if existing.get("pattern") == template.pattern:
                # Actualizar existente
                custom_templates[i] = template_data
                break
        else:
            # Agregar nueva
            custom_templates.append(template_data)
        
        # Guardar plantillas
        try:
            with open(self.template_path, 'w') as f:
                json.dump(custom_templates, f, indent=2)
            
            # Actualizar lista de plantillas
            self.templates.append(template)
            
            return True
        except Exception as e:
            print_colored(f"Error al guardar plantilla personalizada: {str(e)}", "red")
            return False
    
    def find_matching_template(self, query: str, db_schema: Dict[str, Any]) -> Optional[Tuple[QueryTemplate, List[str]]]:
        """
        Busca una plantilla que coincida con la consulta.
        
        Args:
            query: Consulta en lenguaje natural
            db_schema: Esquema de la base de datos
            
        Returns:
            Tupla de (plantilla, parámetros) o None si no hay coincidencia
        """
        for template in self.templates:
            matches, params = template.matches(query)
            if matches:
                # Verificar si la plantilla es aplicable a las tablas existentes
                if template.applicable_tables:
                    available_tables = set(db_schema.get("tables", {}).keys())
                    if not any(table in available_tables for table in template.applicable_tables):
                        continue
                
                return template, params
                
        return None
    
    def log_query(self, query: str, config_id: str, collection_name: str = None, 
                 execution_time: float = 0, cost: float = 0.09, result_count: int = 0):
        """
        Registra una consulta para análisis.
        
        Args:
            query: Consulta en lenguaje natural
            config_id: ID de configuración
            collection_name: Nombre de la colección/tabla
            execution_time: Tiempo de ejecución en segundos
            cost: Costo estimado de la consulta
            result_count: Número de resultados obtenidos
        """
        # Detectar patrón
        pattern = self._detect_pattern(query)
        
        # Registrar en la base de datos
        conn = sqlite3.connect(self.query_log_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO query_log (query, config_id, collection_name, timestamp, execution_time, cost, result_count, pattern)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            query, config_id, collection_name, datetime.now().isoformat(),
            execution_time, cost, result_count, pattern
        ))
        
        # Actualizar estadísticas de patrones
        if pattern:
            cursor.execute(
                "SELECT count, avg_execution_time, avg_cost FROM query_patterns WHERE pattern = ?",
                (pattern,)
            )
            result = cursor.fetchone()
            
            if result:
                # Actualizar patrón existente
                count, avg_exec_time, avg_cost = result
                new_count = count + 1
                new_avg_exec_time = (avg_exec_time * count + execution_time) / new_count
                new_avg_cost = (avg_cost * count + cost) / new_count
                
                cursor.execute('''
                UPDATE query_patterns
                SET count = ?, avg_execution_time = ?, avg_cost = ?, last_updated = ?
                WHERE pattern = ?
                ''', (new_count, new_avg_exec_time, new_avg_cost, datetime.now().isoformat(), pattern))
            else:
                # Insertar nuevo patrón
                cursor.execute('''
                INSERT INTO query_patterns (pattern, count, avg_execution_time, avg_cost, last_updated)
                VALUES (?, 1, ?, ?, ?)
                ''', (pattern, execution_time, cost, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def _detect_pattern(self, query: str) -> Optional[str]:
        """
        Detecta un patrón en la consulta.
        
        Args:
            query: Consulta a analizar
            
        Returns:
            Patrón detectado o None
        """
        normalized_query = query.lower()
        
        # Comprobar patrones predefinidos
        for pattern in self.common_patterns:
            match = re.search(pattern, normalized_query)
            if match:
                # Devolver el patrón con comodines
                entity = match.group(1)
                return pattern.replace(r'(\w+)', f"{entity}")
        
        # Si no se detecta ningún patrón predefinido, intentar generalizar
        words = normalized_query.split()
        if len(words) < 3:
            return None
            
        # Intentar generalizar consultas simples
        if "mostrar" in words or "muestra" in words or "listar" in words or "lista" in words:
            for i, word in enumerate(words):
                if word in ["de", "los", "las", "todos", "todas"]:
                    if i+1 < len(words):
                        return f"lista_de_{words[i+1]}"
        
        return None
    
    def get_common_patterns(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Obtiene los patrones de consulta más comunes.
        
        Args:
            limit: Número máximo de patrones a devolver
            
        Returns:
            Lista de patrones más comunes
        """
        conn = sqlite3.connect(self.query_log_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT pattern, count, avg_execution_time, avg_cost
        FROM query_patterns
        ORDER BY count DESC
        LIMIT ?
        ''', (limit,))
        
        patterns = []
        for row in cursor.fetchall():
            pattern, count, avg_time, avg_cost = row
            patterns.append({
                "pattern": pattern,
                "count": count,
                "avg_execution_time": avg_time,
                "avg_cost": avg_cost,
                "estimated_monthly_cost": round(avg_cost * count * 30 / 7, 2)  # Estimación mensual
            })
        
        conn.close()
        return patterns
    
    def suggest_new_template(self, query: str, sql_query: str) -> Optional[QueryTemplate]:
        """
        Sugiere una nueva plantilla basada en una consulta exitosa.
        
        Args:
            query: Consulta en lenguaje natural
            sql_query: Consulta SQL generada
            
        Returns:
            Plantilla sugerida o None
        """
        # Detectar patrón
        pattern = self._detect_pattern(query)
        if not pattern:
            return None
            
        # Generalizar la consulta SQL
        generalized_sql = sql_query
        
        # Reemplazar valores específicos con marcadores
        # Esto es una simplificación, idealmente se usaría un parser SQL
        tokens = query.lower().split()
        
        # Identificar posibles valores a parametrizar
        for i, token in enumerate(tokens):
            if token.isdigit():
                # Reemplazar números
                generalized_sql = re.sub(r'\b' + re.escape(token) + r'\b', '$1', generalized_sql)
                pattern = pattern.replace(token, "{number}")
            elif '@' in token and '.' in token:
                # Reemplazar emails
                generalized_sql = re.sub(r'\b' + re.escape(token) + r'\b', '$1', generalized_sql)
                pattern = pattern.replace(token, "{value}")
            elif token.startswith('"') or token.startswith("'"):
                # Reemplazar strings
                value = token.strip('"\'')
                if len(value) > 2:  # Evitar reemplazar strings muy cortos
                    generalized_sql = re.sub(r'[\'"]' + re.escape(value) + r'[\'"]', "'$1'", generalized_sql)
                    pattern = pattern.replace(token, "{value}")
        
        # Crear plantilla
        return QueryTemplate(
            pattern=pattern,
            description=f"Plantilla generada automáticamente para: {pattern}",
            sql_template=generalized_sql,
            db_type="sql"
        )
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """
        Genera sugerencias para optimizar consultas.
        
        Returns:
            Lista de sugerencias de optimización
        """
        suggestions = []
        
        # Calcular estadísticas generales
        conn = sqlite3.connect(self.query_log_path)
        cursor = conn.cursor()
        
        # Total de consultas y costo en los últimos 30 días
        cursor.execute('''
        SELECT COUNT(*) as query_count, SUM(cost) as total_cost
        FROM query_log
        WHERE timestamp > datetime('now', '-30 day')
        ''')
        
        row = cursor.fetchone()
        if row:
            query_count, total_cost = row
            
            if query_count and query_count > 100:
                # Si hay muchas consultas en total, sugerir plan de volumen
                suggestions.append({
                    "type": "volume_plan",
                    "query_count": query_count,
                    "total_cost": round(total_cost, 2) if total_cost else 0,
                    "suggestion": f"Considerar negociar un plan por volumen. Actualmente ~{query_count} consultas/mes."
                })
                
                # Sugerir ajustar el TTL del caché según frecuencia
                avg_queries_per_day = query_count / 30
                suggested_ttl = max(3600, min(86400 * 3, 86400 * (100 / avg_queries_per_day)))
                
                suggestions.append({
                    "type": "cache_adjustment",
                    "current_rate": f"{avg_queries_per_day:.1f} consultas/día",
                    "suggestion": f"Ajustar TTL del caché a {suggested_ttl/3600:.1f} horas basado en su patrón de uso"
                })
        
        # Obtener patrones comunes
        common_patterns = self.get_common_patterns(10)
        
        for pattern in common_patterns:
            if pattern["count"] >= 5:
                # Si un patrón se repite mucho, sugerir precompilación
                suggestions.append({
                    "type": "precompile",
                    "pattern": pattern["pattern"],
                    "count": pattern["count"],
                    "estimated_savings": round(pattern["avg_cost"] * pattern["count"] * 0.9, 2),  # 90% de ahorro
                    "suggestion": f"Crear una plantilla SQL para consultas del tipo '{pattern['pattern']}'"
                })
            
            # Si un patrón es costoso pero poco frecuente
            if pattern["avg_cost"] > 0.1 and pattern["count"] < 5:
                suggestions.append({
                    "type": "analyze",
                    "pattern": pattern["pattern"],
                    "avg_cost": pattern["avg_cost"],
                    "suggestion": f"Revisar manualmente consultas del tipo '{pattern['pattern']}' para optimizar"
                })
        
        # Buscar períodos con alta carga para ajustar parámetros
        cursor.execute('''
        SELECT strftime('%Y-%m-%d %H', timestamp) as hour, COUNT(*) as count, SUM(cost) as total_cost
        FROM query_log
        WHERE timestamp > datetime('now', '-7 day')
        GROUP BY hour
        ORDER BY count DESC
        LIMIT 5
        ''')
        
        for row in cursor.fetchall():
            hour, count, total_cost = row
            if count > 20:  # Si hay más de 20 consultas en una hora
                suggestions.append({
                    "type": "load_balancing",
                    "hour": hour,
                    "query_count": count,
                    "total_cost": round(total_cost, 2),
                    "suggestion": f"Alta carga de consultas detectada el {hour} ({count} consultas). Considerar técnicas de agrupación."
                })
        
        # Buscar consultas redundantes (misma consulta en corto tiempo)
        cursor.execute('''
        SELECT query, COUNT(*) as count
        FROM query_log
        WHERE timestamp > datetime('now', '-1 day')
        GROUP BY query
        HAVING COUNT(*) > 3
        ORDER BY COUNT(*) DESC
        LIMIT 5
        ''')
        
        for row in cursor.fetchall():
            query, count = row
            suggestions.append({
                "type": "redundant",
                "query": query,
                "count": count,
                "estimated_savings": round(0.09 * (count - 1), 2),  # Ahorro por no repetir
                "suggestion": f"Implementar caché para la consulta '{query[:50]}...' que se repitió {count} veces"
            })
        
        conn.close()
        return suggestions


    