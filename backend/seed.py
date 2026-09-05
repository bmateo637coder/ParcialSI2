import os
import sys

# Agregar el directorio padre al path para poder importar la app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine, Base
from app.models.user import Role, User
# No usaremos passlib aquí para no complicar el script si no está instalado aún,
# haremos un mock simple o instalaremos passlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_db():
    print("Conectando a la base de datos...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Crear roles
        roles_data = ["Administrador", "Cliente", "Cajero", "Encargado de Sucursal", "Proveedor"]
        for role_name in roles_data:
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                new_role = Role(name=role_name, description=f"Rol de {role_name}")
                db.add(new_role)
                print(f"Rol '{role_name}' creado.")
        
        db.commit()

        # Crear administrador
        admin_role = db.query(Role).filter(Role.name == "Administrador").first()
        admin_email = "admin@fashionstore.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        
        if not admin:
            hashed_pw = pwd_context.hash("admin123")
            new_admin = User(
                first_name="Admin",
                last_name="Principal",
                email=admin_email,
                hashed_password=hashed_pw,
                role_id=admin_role.id
            )
            db.add(new_admin)
            db.commit()
            print(f"Usuario administrador creado: {admin_email} / admin123")
        else:
            print("El administrador ya existe.")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()
        print("Seed completado.")

if __name__ == "__main__":
    seed_db()
