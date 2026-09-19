import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from passlib.context import CryptContext

from app.core.database import Base, SessionLocal, engine
from app.models.branch import Branch
from app.models.catalog import (
    Category,
    Color,
    Collection,
    Product,
    ProductVariant,
    Provider,
    ProviderAccount,
    Season,
    Size,
)
from app.models.inventory import Inventory, InventoryMovement
from app.models.user import Role, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _first_or_create(db, model, **kwargs):
    obj = db.query(model).filter_by(**kwargs).first()
    if obj is None:
        obj = model(**kwargs)
        db.add(obj)
    return obj


def seed_db():
    print("Conectando a la base de datos...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ------------------------------------------------------------------
        # Roles
        # ------------------------------------------------------------------
        roles = {
            "Administrador": "Control total de la plataforma",
            "Cliente": "Usuario regular de la tienda",
            "Cajero": "Gestión de ventas en sucursal",
            "Encargado de Sucursal": "Administración de una sucursal",
            "Proveedor": "Suministra productos a la tienda",
        }
        for name, desc in roles.items():
            _first_or_create(db, Role, name=name, description=desc)
        db.commit()
        print("Roles listos.")

        role = {r.name: r.id for r in db.query(Role).all()}

        # ------------------------------------------------------------------
        # Usuarios (uno por rol + clientes de prueba)
        # ------------------------------------------------------------------
        users = [
            dict(first_name="Admin", last_name="Principal", email="admin@fashionstore.com",
                 password="admin123", role="Administrador", phone="+591 700 000 001"),
            dict(first_name="María", last_name="Gonzales", email="cliente@fashionstore.com",
                 password="cliente123", role="Cliente", phone="+591 700 000 002"),
            dict(first_name="Carlos", last_name="Rojas", email="cliente2@fashionstore.com",
                 password="cliente123", role="Cliente", phone="+591 700 000 003"),
            dict(first_name="Lucía", last_name="Fernández", email="cajero@fashionstore.com",
                 password="cajero123", role="Cajero", phone="+591 700 000 004"),
            dict(first_name="Jorge", last_name="Quispe", email="encargado@fashionstore.com",
                 password="encargado123", role="Encargado de Sucursal", phone="+591 700 000 005"),
            dict(first_name="Inés", last_name="Mamani", email="proveedor@fashionstore.com",
                 password="proveedor123", role="Proveedor", phone="+591 700 000 006"),
        ]
        for u in users:
            user = _first_or_create(db, User, email=u["email"])
            user.first_name = u["first_name"]
            user.last_name = u["last_name"]
            user.phone = u["phone"]
            if not user.hashed_password:
                user.hashed_password = pwd_context.hash(u["password"])
            user.role_id = role[u["role"]]
            user.is_active = True
        db.commit()
        print("Usuarios listos: admin@fashionstore.com / admin123 · cliente@fashionstore.com / cliente123")

        # ------------------------------------------------------------------
        # Catálogo base
        # ------------------------------------------------------------------
        for name in ["Mujer", "Hombre", "Accesorios", "Casual"]:
            _first_or_create(db, Category, name=name)
        db.commit()

        seasons_data = [
            dict(name="Primavera-Verano 2026", year=2026,
                 description="Colección cálida con tejidos ligeros",
                 start_date="2026-09-21", end_date="2027-03-20"),
            dict(name="Otoño-Invierno 2026", year=2026,
                 description="Prendas abrigadas para temporada fría",
                 start_date="2026-03-21", end_date="2026-09-20"),
        ]
        for s in seasons_data:
            season = _first_or_create(db, Season, name=s["name"])
            season.year = s["year"]
            season.description = s["description"]
            season.start_date = s["start_date"]
            season.end_date = s["end_date"]
            season.is_active = True
        db.commit()

        for size in ["XS", "S", "M", "L", "XL", "XXL", "34", "36", "38", "40", "42"]:
            _first_or_create(db, Size, name=size)
        db.commit()

        for color in ["Negro", "Blanco", "Beige", "Gris", "Azul Marino", "Rojo", "Verde Oliva", "Rosa"]:
            _first_or_create(db, Color, name=color)
        db.commit()

        providers_data = [
            dict(name="Confex S.R.L.", contact_email="ventas@confex.bo", nit="1234567012",
                 phone="+591 3 335 8899", address="Av. Monseñor Rivero 500, Santa Cruz"),
            dict(name="Textiles Andinos", contact_email="contacto@textilesandinos.bo", nit="9876543012",
                 phone="+591 2 244 1122", address="Calle México 850, La Paz"),
            dict(name="Moda Latina", contact_email="info@modalatina.bo", nit="5551234001",
                 phone="+591 4 422 3344", address="Av. Heroínas 210, Cochabamba"),
        ]
        for p in providers_data:
            provider = _first_or_create(db, Provider, name=p["name"])
            provider.contact_email = p["contact_email"]
            provider.nit = p["nit"]
            provider.phone = p["phone"]
            provider.address = p["address"]
            provider.is_active = True
        db.commit()

        # ------------------------------------------------------------------
        # Vinculación portal proveedor (proveedor@fashionstore.com -> Moda Latina)
        # ------------------------------------------------------------------
        prov_user = db.query(User).filter(User.email == "proveedor@fashionstore.com").first()
        moda = db.query(Provider).filter(Provider.name == "Moda Latina").first()
        if prov_user and moda:
            existing_account = db.query(ProviderAccount).filter_by(user_id=prov_user.id).first()
            if existing_account is None:
                db.add(ProviderAccount(user_id=prov_user.id, provider_id=moda.id))
                db.commit()
            print("Portal proveedor vinculado: proveedor@fashionstore.com -> Moda Latina.")

        primavera = db.query(Season).filter(Season.name == "Primavera-Verano 2026").first()
        otono = db.query(Season).filter(Season.name == "Otoño-Invierno 2026").first()

        _first_or_create(db, Collection, name="Atardecer", season_id=primavera.id, is_active=True)
        _first_or_create(db, Collection, name="Clásicos", season_id=otono.id, is_active=True)
        db.commit()
        print("Catálogo base listo.")

        # ------------------------------------------------------------------
        # Productos
        # ------------------------------------------------------------------
        def cat(name: str) -> Category:
            return db.query(Category).filter(Category.name == name).first()

        def prov(name: str) -> Provider:
            return db.query(Provider).filter(Provider.name == name).first()

        def get_season(name: str) -> Season:
            return db.query(Season).filter(Season.name == name).first()

        def get_collection(name: str) -> Collection:
            return db.query(Collection).filter(Collection.name == name).first()

        products_data = [
            dict(
                name="Vestido Floral Verano",
                description="Vestido ligero con estampado floral, corte fluido y tejido de algodón orgánico. Ideal para días cálidos.",
                base_price=289.00,
                category_id=cat("Mujer").id,
                season_id=get_season("Primavera-Verano 2026").id,
                collection_id=get_collection("Atardecer").id,
                provider_id=prov("Moda Latina").id,
                image_url="https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?auto=format&fit=crop&q=80&w=600",
            ),
            dict(
                name="Camiseta Premium Básica",
                description="Camiseta de algodón peinado 100%, cuello redondo y costuras reforzadas. Básico esencial para cualquier guardarropa.",
                base_price=99.50,
                category_id=cat("Hombre").id,
                season_id=get_season("Otoño-Invierno 2026").id,
                provider_id=prov("Confex S.R.L.").id,
                image_url="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&q=80&w=600",
            ),
            dict(
                name="Chaqueta de Cuero Clásica",
                description="Chaqueta de cuero genuino con forro térmico. Un clásico atemporal con corte moderno y cierre metálico de alta calidad.",
                base_price=899.00,
                category_id=cat("Hombre").id,
                season_id=get_season("Otoño-Invierno 2026").id,
                collection_id=get_collection("Clásicos").id,
                provider_id=prov("Textiles Andinos").id,
                image_url="https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&q=80&w=600",
            ),
            dict(
                name="Jean Slim Azul",
                description="Jeans de corte slim con denim de alta elasticidad. Comodidad todo el día sin perder la forma.",
                base_price=349.00,
                category_id=cat("Mujer").id,
                season_id=get_season("Otoño-Invierno 2026").id,
                provider_id=prov("Confex S.R.L.").id,
                image_url="https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&q=80&w=600",
            ),
            dict(
                name="Suéter de Lana Merino",
                description="Suéter tejido en lana merino extrafina. Liviano, abrigado y con un acabado elegante.",
                base_price=420.00,
                category_id=cat("Mujer").id,
                season_id=get_season("Otoño-Invierno 2026").id,
                collection_id=get_collection("Clásicos").id,
                provider_id=prov("Textiles Andinos").id,
                image_url="https://images.unsplash.com/photo-1576566588028-4147f3842f27?auto=format&fit=crop&q=80&w=600",
            ),
            dict(
                name="Blazer Entallado",
                description="Blazer estructurado con hombros definidos y forro de satén. Perfecto para ocasiones formales.",
                base_price=650.00,
                category_id=cat("Mujer").id,
                season_id=get_season("Primavera-Verano 2026").id,
                provider_id=prov("Moda Latina").id,
                image_url="https://images.unsplash.com/photo-1591047139829-d91aecb6caea?auto=format&fit=crop&q=80&w=600",
            ),
            dict(
                name="Camisa Oxford Blanca",
                description="Camisa clásica oxford en algodón de largo tendido. Versátil para oficina o casual.",
                base_price=180.00,
                category_id=cat("Hombre").id,
                season_id=get_season("Otoño-Invierno 2026").id,
                provider_id=prov("Confex S.R.L.").id,
                image_url="https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&q=80&w=600",
            ),
            dict(
                name="Vestido de Noche Elegante",
                description="Vestido largo con escote en V y caída de seda. Diseñado para brillar en eventos especiales.",
                base_price=780.00,
                category_id=cat("Mujer").id,
                season_id=get_season("Primavera-Verano 2026").id,
                collection_id=get_collection("Atardecer").id,
                provider_id=prov("Moda Latina").id,
                image_url="https://images.unsplash.com/photo-1566174053879-31528523f8ae?auto=format&fit=crop&q=80&w=600",
            ),
            dict(
                name="Hoodie Deportivo",
                description="Buzo con capucha en algodón felpa, bolsillo canguro y ajuste relajado. Tu compañero diario.",
                base_price=210.00,
                category_id=cat("Casual").id,
                season_id=get_season("Primavera-Verano 2026").id,
                provider_id=prov("Textiles Andinos").id,
                image_url="https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&q=80&w=600",
            ),
            dict(
                name="Falda Midi Plisada",
                description="Falda midi con plisados finos y cintura elástica. Movimiento y estilo en cada paso.",
                base_price=260.00,
                category_id=cat("Mujer").id,
                season_id=get_season("Primavera-Verano 2026").id,
                provider_id=prov("Moda Latina").id,
                image_url="https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?auto=format&fit=crop&q=80&w=600",
            ),
        ]

        for p in products_data:
            existing = db.query(Product).filter(Product.name == p["name"]).first()
            if existing:
                continue
            db.add(Product(**p))

        db.commit()
        print("Productos listos.")

        # ------------------------------------------------------------------
        # Variantes (talla + color)
        # ------------------------------------------------------------------
        def get_size(name):
            return db.query(Size).filter(Size.name == name).first()

        def get_color(name):
            return db.query(Color).filter(Color.name == name).first()

        variant_specs = {
            "Vestido Floral Verano": [("S", "Rosa"), ("M", "Rosa"), ("L", "Rosa"),
                                      ("S", "Blanco"), ("M", "Blanco"), ("L", "Blanco")],
            "Camiseta Premium Básica": [("M", "Blanco"), ("L", "Blanco"), ("XL", "Blanco"), ("XXL", "Blanco"),
                                        ("M", "Gris"), ("L", "Gris"), ("XL", "Gris")],
            "Jean Slim Azul": [("34", "Azul Marino"), ("36", "Azul Marino"), ("38", "Azul Marino"),
                               ("36", "Negro"), ("38", "Negro")],
            "Suéter de Lana Merino": [("S", "Beige"), ("M", "Beige"), ("L", "Beige"), ("M", "Gris")],
            "Blazer Entallado": [("S", "Negro"), ("M", "Negro"), ("L", "Negro")],
            "Camisa Oxford Blanca": [("M", "Blanco"), ("L", "Blanco"), ("XL", "Blanco")],
            "Chaqueta de Cuero Clásica": [("M", "Negro"), ("L", "Negro"), ("XL", "Negro")],
            "Vestido de Noche Elegante": [("S", "Negro"), ("M", "Negro")],
            "Hoodie Deportivo": [("M", "Verde Oliva"), ("L", "Verde Oliva"), ("XL", "Gris")],
            "Falda Midi Plisada": [("S", "Rosa"), ("M", "Rosa"), ("M", "Negro")],
        }

        sku_counter = 0
        for product_name, combos in variant_specs.items():
            product = db.query(Product).filter(Product.name == product_name).first()
            if product is None or product.variants:
                continue
            for size, color in combos:
                sku_counter += 1
                db.add(ProductVariant(
                    product_id=product.id,
                    size_id=get_size(size).id,
                    color_id=get_color(color).id,
                    sku=f"FS-{sku_counter:05d}",
                ))
        db.commit()
        print("Variantes listas.")

        # ------------------------------------------------------------------
        # Sucursales
        # ------------------------------------------------------------------
        branches_data = [
            ("Sucursal Equipetrol", "Santa Cruz", "Av. San Martín 320, Equipetrol",
             "+591 3 345 2233", -17.790877, -63.185281),
            ("Sucursal Ayacucho", "Santa Cruz", "Calle Ayacucho 150, Centro",
             "+591 3 334 1100", -17.783383, -63.182030),
            ("Sucursal Sopocachi", "La Paz", "Av. 6 de Agosto 2200, Sopocachi",
             "+591 2 244 5566", -16.509931, -68.133519),
            ("Sucursal Centro", "Cochabamba", "Av. Heroínas 410, Centro",
             "+591 4 422 7788", -17.393541, -66.157012),
            ("Sucursal Tarija", "Tarija", "Calle 15 de Abril 89",
             "+591 4 663 1122", -21.535498, -64.729562),
        ]
        for name, city, address, phone, lat, lng in branches_data:
            branch = _first_or_create(db, Branch, name=name)
            branch.city = city
            branch.address = address
            branch.phone = phone
            branch.latitude = lat
            branch.longitude = lng
            branch.is_active = True
        db.commit()
        print("Sucursales listas.")

        # ------------------------------------------------------------------
        # Inventario por sucursal (CU11/CU21) con el movimiento INGRESO inicial
        # ------------------------------------------------------------------
        admin_user = db.query(User).filter(User.email == "admin@fashionstore.com").first()
        branches = db.query(Branch).all()
        variants = db.query(ProductVariant).order_by(ProductVariant.id).all()

        # Distribución base: cada variante disponible en 2-3 sucursales con cantidades variadas
        import random
        random.seed(42)
        per_variant = {
            v.id: {
                b.id: random.choice([6, 8, 10, 12, 15, 20, 25]) if idx % 3 == 0 else
                      random.choice([3, 4, 5, 6]) if idx % 3 == 1 else
                      random.choice([1, 2, 3]) if random.random() > 0.6 else 0
                for idx, b in enumerate(branches)
            }
            for v in variants
        }

        inventory_created = 0
        for v in variants:
            for b in branches:
                qty = per_variant[v.id][b.id]
                if qty <= 0:
                    continue
                existing = db.query(Inventory).filter_by(variant_id=v.id, branch_id=b.id).first()
                if existing:
                    continue
                inv = Inventory(variant_id=v.id, branch_id=b.id, available=qty)
                db.add(inv)
                db.flush()
                db.add(InventoryMovement(
                    inventory_id=inv.id,
                    movement_type="INGRESO",
                    quantity=qty,
                    reason="Stock inicial",
                    user_id=admin_user.id,
                ))
                inventory_created += 1
        db.commit()
        print(f"Inventario listo: {inventory_created} registros con ingreso inicial.")

    except Exception as e:
        print(f"Error durante el seed: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        print("Seed completado correctamente.")


if __name__ == "__main__":
    seed_db()