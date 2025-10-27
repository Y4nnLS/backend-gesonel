#!/usr/bin/env python3
"""
Script para criar as tabelas do banco de dados
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Adiciona o diretório app ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.api.core.db import engine
from app.api.models.audio_file import Base

def create_tables():
    """Cria todas as tabelas no banco de dados"""
    try:
        print("🔧 Criando tabelas no banco de dados...")
        
        # Cria todas as tabelas
        Base.metadata.create_all(bind=engine)
        
        print("✅ Tabelas criadas com sucesso!")
        print("📋 Tabelas criadas:")
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
            
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False
    
    return True

def drop_tables():
    """Remove todas as tabelas do banco de dados"""
    try:
        print("🗑️ Removendo tabelas do banco de dados...")
        
        # Remove todas as tabelas
        Base.metadata.drop_all(bind=engine)
        
        print("✅ Tabelas removidas com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao remover tabelas: {e}")
        return False
    
    return True

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerenciar tabelas do banco de dados")
    parser.add_argument("--drop", action="store_true", help="Remove todas as tabelas")
    parser.add_argument("--recreate", action="store_true", help="Remove e recria todas as tabelas")
    
    args = parser.parse_args()
    
    if args.drop:
        drop_tables()
    elif args.recreate:
        print("🔄 Recriando tabelas...")
        drop_tables()
        create_tables()
    else:
        create_tables()

if __name__ == "__main__":
    main()
