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
    Season,
    Size,
)
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

        admin_role = db.query(Role).filter(Role.name == "Administrador").first()
        cliente_role = db.query(Role).filter(Role.name == "Cliente").first()

        # ------------------------------------------------------------------
        # Usuarios
        # ------------------------------------------------------------------
        admin = _first_or_create(
            db, User,
            first_name="Admin", last_name="Principal",
            email="admin@fashionstore.com",
        )
        if not admin.hashed_password:
            admin.hashed_password = pwd_context.hash("admin123")
        admin.role_id = admin_role.id

        cliente = _first_or_create(
            db, User,
            first_name="María", last_name="Gonzales",
            email="cliente@fashionstore.com",
        )
        if not cliente.hashed_password:
            cliente.hashed_password = pwd_context.hash("cliente123")
        cliente.role_id = cliente_role.id
        db.commit()
        print("Usuarios listos. Admin: admin@fashionstore.com / admin123")

        # ------------------------------------------------------------------
        # Catálogo base
        # ------------------------------------------------------------------
        categories = ["Mujer", "Hombre", "Accesorios", "Casual"]
        for name in categories:
            _first_or_create(db, Category, name=name)
        db.commit()

        seasons = {
            "Primavera-Verano 2026": None,
            "Otoño-Invierno 2026": None,
        }
        for name in seasons:
            _first_or_create(db, Season, name=name)
        db.commit()

        for size in ["XS", "S", "M", "L", "XL", "XXL", "34", "36", "38", "40", "42"]:
            _first_or_create(db, Size, name=size)
        db.commit()

        for color in ["Negro", "Blanco", "Beige", "Gris", "Azul Marino", "Rojo", "Verde Oliva", "Rosa"]:
            _first_or_create(db, Color, name=color)
        db.commit()

        providers = {
            "Confex S.R.L.": "ventas@confex.bo",
            "Textiles Andinos": "contacto@textilesandinos.bo",
            "Moda Latina": "info@modalatina.bo",
        }
        for name, email in providers.items():
            _first_or_create(db, Provider, name=name, contact_email=email)
        db.commit()

        primavera = db.query(Season).filter(Season.name == "Primavera-Verano 2026").first()
        otono = db.query(Season).filter(Season.name == "Otoño-Invierno 2026").first()

        colection_atardecer = _first_or_create(db, Collection, name="Atardecer", season_id=primavera.id)
        colection_clasicos = _first_or_create(db, Collection, name="Clásicos", season_id=otono.id)
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
        # Variantes (talla + color + stock)
        # ------------------------------------------------------------------
        def get_size(name):
            return db.query(Size).filter(Size.name == name).first()

        def get_color(name):
            return db.query(Color).filter(Color.name == name).first()

        vestido = db.query(Product).filter(Product.name == "Vestido Floral Verano").first()
        camiseta = db.query(Product).filter(Product.name == "Camiseta Premium Básica").first()
        jean = db.query(Product).filter(Product.name == "Jean Slim Azul").first()

        if vestido and not vestido.variants:
            for size in ["S", "M", "L"]:
                for color, stock in [("Rosa", 12), ("Blanco", 8)]:
                    db.add(
                        ProductVariant(
                            product_id=vestido.id,
                            size_id=get_size(size).id,
                            color_id=get_color(color).id,
                            sku=f"VST-{size}-{color[:2].upper()}",
                            stock=stock,
                        )
                    )

        if camiseta and not camiseta.variants:
            for size in ["M", "L", "XL", "XXL"]:
                db.add(
                    ProductVariant(
                        product_id=camiseta.id,
                        size_id=get_size(size).id,
                        color_id=get_color("Blanco").id,
                        sku=f"CMT-{size}-BL",
                        stock=25,
                    )
                )

        if jean and not jean.variants:
            for size in ["34", "36", "38"]:
                db.add(
                    ProductVariant(
                        product_id=jean.id,
                        size_id=get_size(size).id,
                        color_id=get_color("Azul Marino").id,
                        sku=f"JNS-{size}-AM",
                        stock=15,
                    )
                )
        db.commit()
        print("Variantes listas.")

        # ------------------------------------------------------------------
        # Sucursales
        # ------------------------------------------------------------------
        branches = [
            ("Sucursal Equipetrol", "Santa Cruz", "Av. San Martín 320, Equipetrol", "+591 3 345 2233"),
            ("Sucursal Ayacucho", "Santa Cruz", "Calle Ayacucho 150, Centro", "+591 3 334 1100"),
            ("Sucursal Sopocachi", "La Paz", "Av. 6 de Agosto 2200, Sopocachi", "+591 2 244 5566"),
            ("Sucursal Centro", "Cochabamba", "Av. Heroínas 410, Centro", "+591 4 422 7788"),
            ("Sucursal Tarija", "Tarija", "Calle 15 de Abril 89", "+591 4 663 1122"),
        ]
        for name, city, address, phone in branches:
            _first_or_create(db, Branch, name=name, city=city, address=address, phone=phone, is_active=True)
        db.commit()
        print("Sucursales listas.")

    except Exception as e:
        print(f"Error durante el seed: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        print("Seed completado correctamente.")


if __name__ == "__main__":
    seed_db()