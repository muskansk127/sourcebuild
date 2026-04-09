from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import uuid
import warnings
from typing import Any, cast
from datetime import datetime
from bson import ObjectId

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r".*pkg_resources is deprecated as an API.*",
        category=UserWarning,
    )
    try:
        import mongomock
    except Exception:
        mongomock = None


load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "please-change-this-in-production")
    app.permanent_session_lifetime = timedelta(days=7)
    # File upload config
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB
    static_folder = app.static_folder or "static"
    app.config["UPLOAD_FOLDER"] = os.path.join(static_folder, "uploads")
    app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    app.config["MONGO_DB_NAME"] = os.getenv("MONGO_DB_NAME", "sourcebuild_db")
    app.config["MONGO_MOCK_FALLBACK"] = os.getenv("MONGO_MOCK_FALLBACK", "1") == "1"
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    def connect_mongo(uri: str) -> MongoClient:
        return MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000, socketTimeoutMS=5000)

    db_available = False
    db_error = None
    db_mode = "unavailable"
    client = None
    flask_env = os.getenv("FLASK_ENV", "development").lower()
    is_production = flask_env == "production"

    try:
        client = connect_mongo(app.config["MONGO_URI"])
        client.admin.command('ping')
        db_available = True
        db_mode = "mongodb"
        print("[MongoDB] Connected successfully")
    except Exception as e:
        can_use_mock = app.config["MONGO_MOCK_FALLBACK"] and not is_production and mongomock is not None
        if can_use_mock:
            mock_module = cast(Any, mongomock)
            client = mock_module.MongoClient()
            db_available = True
            db_mode = "mock"
            db_error = None
            print("[MongoDB] Primary connection failed, using in-memory mock database for development")
        else:
            db_error = str(e)
            print(f"[MongoDB] Connection failed: {e}")
            if app.config["MONGO_MOCK_FALLBACK"] and mongomock is None:
                print("[MongoDB] Mock fallback requested but mongomock is not installed")

    db: Any = client[app.config["MONGO_DB_NAME"]] if db_available and client is not None else None
    customers: Any = db["customers"] if db is not None else None
    engineers: Any = db["engineers"] if db is not None else None
    cost_estimations: Any = db["cost_estimations"] if db is not None else None
    area_images: Any = db["area_images"] if db is not None else None
    plan_images: Any = db["plan_images"] if db is not None else None

    db_required_endpoints = {
        "register_customer",
        "register_engineer",
        "login",
        "dashboard_customer",
        "dashboard_engineer",
        "upload_plan_image",
        "delete_plan_image",
        "estimate_cost",
        "upload_area_image",
        "delete_area_image",
    }

    @app.before_request
    def require_database_for_protected_routes():
        if db_available:
            return None

        endpoint = request.endpoint
        if endpoint in db_required_endpoints:
            flash("Database is unavailable. Please configure MONGO_URI and restart the app.", "error")
            return redirect(url_for("home"))
        return None

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/health")
    def health():
        status_code = 200 if db_available else 503
        return jsonify({
            "status": "ok" if db_available else "degraded",
            "database": "connected" if db_available else "unavailable",
            "database_mode": db_mode,
            "database_error": db_error,
        }), status_code

    @app.route("/register_customer", methods=["GET", "POST"])
    def register_customer():
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").lower().strip()
            phone = request.form.get("phone", "").strip()
            location = request.form.get("location", "").strip()
            land_size = request.form.get("land_size", "").strip()
            password = request.form.get("password", "")

            if not (full_name and email and phone and location and land_size and password):
                flash("All fields are required", "error")
                return render_template("register_customer.html")

            if customers.find_one({"email": email}):
                flash("Email already registered", "error")
                return render_template("register_customer.html")

            hashed = generate_password_hash(password)
            customers.insert_one({
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "location": location,
                "land_size": land_size,
                "password": hashed,
                "role": "customer"
            })
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

        return render_template("register_customer.html")

    @app.route("/register_engineer", methods=["GET", "POST"])
    def register_engineer():
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").lower().strip()
            phone = request.form.get("phone", "").strip()
            qualification = request.form.get("qualification", "").strip()
            experience = request.form.get("experience", "").strip()
            portfolio = request.form.get("portfolio", "").strip()
            password = request.form.get("password", "")

            if not (full_name and email and phone and qualification and experience and password):
                flash("All required fields must be filled", "error")
                return render_template("register_engineer.html")

            if engineers.find_one({"email": email}):
                flash("Email already registered", "error")
                return render_template("register_engineer.html")

            hashed = generate_password_hash(password)
            engineers.insert_one({
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "qualification": qualification,
                "experience": experience,
                "portfolio": portfolio,
                "password": hashed,
                "role": "engineer"
            })
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

        return render_template("register_engineer.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            role = request.form.get("role")
            email = request.form.get("email", "").lower().strip()
            password = request.form.get("password", "")

            if role not in {"customer", "engineer"}:
                flash("Invalid role selected", "error")
                return render_template("login.html")

            collection = customers if role == "customer" else engineers
            user = collection.find_one({"email": email})
            if not user or not check_password_hash(user.get("password", ""), password):
                flash("Invalid credentials", "error")
                return render_template("login.html")

            session.permanent = True
            session["user_id"] = str(user.get("_id"))
            session["role"] = role
            session["full_name"] = user.get("full_name")

            if role == "customer":
                return redirect(url_for("dashboard_customer"))
            return redirect(url_for("dashboard_engineer"))

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("home"))

    @app.route("/dashboard_customer")
    def dashboard_customer():
        if session.get("role") != "customer":
            return redirect(url_for("login"))
        engineer_list = list(engineers.find({}, {"full_name": 1, "qualification": 1, "experience": 1, "portfolio": 1}))
        images = list(area_images.find({"user_id": session.get("user_id")}).sort("created_at", -1))
        # Build plan map for customer's images
        img_ids = [img.get("_id") for img in images]
        plan_map = {}
        if img_ids:
            for p in plan_images.find({"area_image_id": {"$in": img_ids}}):
                key = str(p.get("area_image_id"))
                plan_map.setdefault(key, []).append(p)
        return render_template("dashboard_customer.html", engineers=engineer_list, images=images, plan_map=plan_map)

    @app.route("/dashboard_engineer")
    def dashboard_engineer():
        if session.get("role") != "engineer":
            return redirect(url_for("login"))
        estimates = list(cost_estimations.find().sort("created_at", -1))
        # Show recent area images from customers for engineers to respond to
        images = list(area_images.find().sort("created_at", -1))
        # Map area_image_id -> plan images list
        plan_map = {}
        for p in plan_images.find():
            key = str(p.get("area_image_id"))
            plan_map.setdefault(key, []).append(p)
        return render_template("dashboard_engineer.html", estimates=estimates, area_images=images, plan_map=plan_map)

    @app.route("/upload_plan_image/<area_image_id>", methods=["POST"])
    def upload_plan_image(area_image_id: str):
        if session.get("role") != "engineer":
            return redirect(url_for("login"))
        try:
            src = area_images.find_one({"_id": ObjectId(area_image_id)})
        except Exception:
            src = None
        if not src:
            flash("Area image not found", "error")
            return redirect(url_for("dashboard_engineer"))
        if "image" not in request.files:
            flash("No file part", "error")
            return redirect(url_for("dashboard_engineer"))
        file = request.files["image"]
        filename = file.filename or ""
        if filename == "":
            flash("No selected file", "error")
            return redirect(url_for("dashboard_engineer"))
        if file and _allowed_file(filename):
            safe_name = secure_filename(filename)
            unique_name = f"plan_{uuid.uuid4().hex}_{safe_name}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(save_path)
            plan_images.insert_one({
                "area_image_id": ObjectId(area_image_id),
                "engineer_id": session.get("user_id"),
                "engineer_name": session.get("full_name"),
                "filename": unique_name,
                "created_at": datetime.utcnow(),
            })
            flash("Plan image uploaded", "success")
        else:
            flash("Unsupported file type. Use PNG/JPG/JPEG/WEBP.", "error")
        return redirect(url_for("dashboard_engineer"))

    @app.route("/delete_plan_image/<plan_id>", methods=["POST"])
    def delete_plan_image(plan_id: str):
        if session.get("role") != "engineer":
            return redirect(url_for("login"))
        try:
            plan = plan_images.find_one({"_id": ObjectId(plan_id), "engineer_id": session.get("user_id")})
        except Exception:
            plan = None
        if not plan:
            flash("Plan not found or you don't have permission to delete it", "error")
            return redirect(url_for("dashboard_engineer"))
        # Remove file from disk
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], plan.get("filename", ""))
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            # Ignore file deletion errors; still remove DB record
            pass
        plan_images.delete_one({"_id": plan["_id"]})
        flash("Plan deleted successfully", "success")
        return redirect(url_for("dashboard_engineer"))

    @app.route("/estimate_cost", methods=["POST"])
    def estimate_cost():
        if session.get("role") != "customer":
            return redirect(url_for("login"))
        try:
            area = float(request.form.get("area", 0))
        except ValueError:
            flash("Invalid area value", "error")
            return redirect(url_for("dashboard_customer"))
        material = request.form.get("material") or "Basic"
        rate_map = {"Basic": 1200, "Standard": 1600, "Premium": 2000}
        rate = rate_map.get(material, 1200)
        estimated_cost = int(area * rate)
        
        # Calculate suggested cost within ₹70k-₹80k range
        suggested_area = None
        suggested_cost = None
        if 70000 <= estimated_cost <= 80000:
            # Current estimate is already in target range
            suggested_area = area
            suggested_cost = estimated_cost
        elif estimated_cost < 70000:
            # Suggest larger area to reach target range
            suggested_area = int(75000 / rate)
            suggested_cost = int(suggested_area * rate)
        else:
            # Suggest smaller area to reach target range
            suggested_area = int(75000 / rate)
            suggested_cost = int(suggested_area * rate)
        
        doc = {
            "customer_name": session.get("full_name"),
            "area": area,
            "material": material,
            "rate": rate,
            "estimated_cost": estimated_cost,
            "suggested_area": suggested_area,
            "suggested_cost": suggested_cost,
        }
        cost_estimations.insert_one(doc)
        
        # Show both original estimate and suggested cost
        if suggested_area != area:
            flash(f"Your estimate: ₹{estimated_cost:,} for {area} sqft | Suggested: ₹{suggested_cost:,} for {suggested_area} sqft", "success")
        else:
            flash(f"Estimated cost: ₹{estimated_cost:,} for {area} sqft", "success")
        return redirect(url_for("dashboard_customer"))

    def _allowed_file(filename: str) -> bool:
        allowed = {"png", "jpg", "jpeg", "webp"}
        return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

    @app.route("/upload_area_image", methods=["POST"])
    def upload_area_image():
        if session.get("role") != "customer":
            return redirect(url_for("login"))
        if "image" not in request.files:
            flash("No file part", "error")
            return redirect(url_for("dashboard_customer"))
        file = request.files["image"]
        filename = file.filename or ""
        if filename == "":
            flash("No selected file", "error")
            return redirect(url_for("dashboard_customer"))
        if file and _allowed_file(filename):
            safe_name = secure_filename(filename)
            unique_name = f"{uuid.uuid4().hex}_{safe_name}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(save_path)
            area_images.insert_one({
                "user_id": session.get("user_id"),
                "customer_name": session.get("full_name"),
                "filename": unique_name,
                "created_at": datetime.utcnow(),
            })
            flash("Image uploaded", "success")
        else:
            flash("Unsupported file type. Use PNG/JPG/JPEG/WEBP.", "error")
        return redirect(url_for("dashboard_customer"))

    @app.route("/delete_area_image/<image_id>", methods=["POST"])
    def delete_area_image(image_id: str):
        if session.get("role") != "customer":
            return redirect(url_for("login"))
        try:
            img = area_images.find_one({"_id": ObjectId(image_id), "user_id": session.get("user_id")})
        except Exception:
            img = None
        if not img:
            flash("Image not found", "error")
            return redirect(url_for("dashboard_customer"))
        # Remove file from disk
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], img.get("filename", ""))
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            # Ignore file deletion errors; still remove DB record
            pass
        area_images.delete_one({"_id": img["_id"]})
        flash("Image deleted", "success")
        return redirect(url_for("dashboard_customer"))

    return app


if __name__ == "__main__":
    app = create_app()
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)


