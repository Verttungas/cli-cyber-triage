#!/usr/bin/env python3
"""
Quick Test Script para Cyber-Triage CLI
Verifica que todos los componentes estén funcionando
"""

import os
import sys
from pathlib import Path

def test_env_variables():
    """Test 1: Variables de entorno"""
    print("🧪 Test 1: Variables de Entorno")
    print("-" * 50)
    
    required_vars = {
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
        'CYBERHAVEN_API_KEY': os.getenv('CYBERHAVEN_API_KEY')
    }
    
    optional_vars = {
        'AWS_S3_BUCKET': os.getenv('AWS_S3_BUCKET'),
        'EVIDENCE_DIR': os.getenv('EVIDENCE_DIR', './evidencia_temp')
    }
    
    all_ok = True
    
    for var, value in required_vars.items():
        if value and value != f"your-{var.lower().replace('_', '-')}-here":
            print(f"  ✅ {var}: Configurada")
        else:
            print(f"  ❌ {var}: NO configurada")
            all_ok = False
    
    for var, value in optional_vars.items():
        if value:
            print(f"  ℹ️  {var}: {value}")
    
    print()
    return all_ok


def test_imports():
    """Test 2: Imports de módulos"""
    print("🧪 Test 2: Imports de Módulos")
    print("-" * 50)
    
    modules = [
        ('rich', 'Rich terminal UI'),
        ('google.genai', 'Gemini API'),
        ('boto3', 'AWS SDK'),
        ('requests', 'HTTP client'),
        ('sqlite3', 'SQLite DB'),
        ('PIL', 'Pillow (imágenes)')
    ]
    
    all_ok = True
    
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}: OK ({description})")
        except ImportError as e:
            print(f"  ❌ {module_name}: FALTA ({description})")
            print(f"     Error: {e}")
            all_ok = False
    
    print()
    return all_ok


def test_custom_modules():
    """Test 3: Módulos custom del proyecto"""
    print("🧪 Test 3: Módulos Custom")
    print("-" * 50)
    
    modules = [
        'db_manager',
        'gemini_analyzer',
        'evidence_downloader'
    ]
    
    all_ok = True
    
    for module_name in modules:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}.py: OK")
        except ImportError as e:
            print(f"  ❌ {module_name}.py: ERROR")
            print(f"     {e}")
            all_ok = False
    
    print()
    return all_ok


def test_directories():
    """Test 4: Directorios necesarios"""
    print("🧪 Test 4: Estructura de Directorios")
    print("-" * 50)
    
    dirs = [
        'data',
        'evidencia_temp',
        'logs',
        'prompts'
    ]
    
    all_ok = True
    
    for dir_name in dirs:
        path = Path(dir_name)
        if path.exists() and path.is_dir():
            print(f"  ✅ {dir_name}/: Existe")
        else:
            print(f"  ⚠️  {dir_name}/: No existe (se creará)")
            path.mkdir(exist_ok=True)
    
    print()
    return all_ok


def test_prompts():
    """Test 5: Archivos de prompts"""
    print("🧪 Test 5: Archivos de Prompts")
    print("-" * 50)
    
    prompts = [
        'prompts/system_prompt.md',
        'prompts/rag_template.md'
    ]
    
    all_ok = True
    
    for prompt_file in prompts:
        path = Path(prompt_file)
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"  ✅ {prompt_file}: OK ({size_kb:.1f} KB)")
        else:
            print(f"  ❌ {prompt_file}: NO existe")
            all_ok = False
    
    print()
    return all_ok


def test_database():
    """Test 6: Base de datos"""
    print("🧪 Test 6: Base de Datos SQLite")
    print("-" * 50)
    
    try:
        from db_manager import DatabaseManager
        
        db = DatabaseManager()
        stats = db.get_database_stats()
        
        print(f"  ✅ Database conectada")
        print(f"  ℹ️  Total incidentes: {sum(stats.get('incidents_by_status', {}).values())}")
        print(f"  ℹ️  Total análisis: {stats.get('total_analyses', 0)}")
        print(f"  ℹ️  Total feedback: {stats.get('total_feedback', 0)}")
        print()
        return True
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print()
        return False


def test_gemini_connection():
    """Test 7: Conexión con Gemini"""
    print("🧪 Test 7: Conexión con Gemini API")
    print("-" * 50)
    
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key or api_key == 'your-gemini-api-key-here':
        print("  ⚠️  GEMINI_API_KEY no configurada - Saltando test")
        print()
        return True
    
    try:
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        # Test simple de conexión
        response = client.models.generate_content(
            model='gemini-3-pro-preview',
            contents='Responde solo: OK',
            config={'temperature': 0, 'max_output_tokens': 10}
        )
        
        if 'OK' in response.text.upper():
            print(f"  ✅ Gemini 3 Pro: Conectado y respondiendo")
        else:
            print(f"  ⚠️  Gemini respondió pero respuesta inesperada: {response.text[:50]}")
        
        print()
        return True
    
    except Exception as e:
        print(f"  ❌ Error conectando con Gemini: {e}")
        print()
        return False


def test_aws_connection():
    """Test 8: Conexión con AWS S3 (opcional)"""
    print("🧪 Test 8: Conexión con AWS S3 (opcional)")
    print("-" * 50)
    
    try:
        import boto3
        
        s3 = boto3.client('s3')
        
        # Test básico: intentar listar buckets
        try:
            response = s3.list_buckets()
            print(f"  ✅ AWS S3: Conectado")
            print(f"  ℹ️  IAM credentials detectadas")
        except Exception as e:
            if 'credentials' in str(e).lower():
                print(f"  ⚠️  AWS credentials no configuradas")
                print(f"     Esto es OK si usas IAM Role en EC2")
            else:
                print(f"  ⚠️  Error: {e}")
        
        print()
        return True
    
    except Exception as e:
        print(f"  ❌ boto3 no disponible: {e}")
        print()
        return False


def main():
    print()
    print("=" * 60)
    print("  🛡️  CYBER-TRIAGE CLI - QUICK TEST")
    print("=" * 60)
    print()
    
    tests = [
        test_env_variables,
        test_imports,
        test_custom_modules,
        test_directories,
        test_prompts,
        test_database,
        test_gemini_connection,
        test_aws_connection
    ]
    
    results = []
    
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test falló con excepción: {e}")
            results.append(False)
    
    print()
    print("=" * 60)
    print("  📊 RESUMEN")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n  Tests pasados: {passed}/{total}")
    
    if passed == total:
        print("\n  ✅ TODOS LOS TESTS PASARON")
        print("\n  Sistema listo para usar:")
        print("    python3 cyber_triage_cli.py")
        print()
        return 0
    else:
        print("\n  ⚠️  ALGUNOS TESTS FALLARON")
        print("\n  Revisa los errores arriba y:")
        print("    1. Verifica que .env esté configurado")
        print("    2. Instala dependencias: pip3 install -r requirements.txt --break-system-packages")
        print("    3. Verifica archivos de prompts en ./prompts/")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
