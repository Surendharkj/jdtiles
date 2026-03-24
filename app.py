import os
from datetime import timedelta

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson.objectid import ObjectId

from config import MONGO_URI, FLASK_SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER_TILES = os.path.join("static", "images", "tiles")
UPLOAD_FOLDER_PROPERTIES = os.path.join("static", "images", "properties")
UPLOAD_FOLDER_TILES_VIDEOS = os.path.join("static", "videos", "tiles")
UPLOAD_FOLDER_PROPERTIES_VIDEOS = os.path.join("static", "videos", "properties")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "webm"}

os.makedirs(os.path.join(BASE_DIR, UPLOAD_FOLDER_TILES), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, UPLOAD_FOLDER_PROPERTIES), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, UPLOAD_FOLDER_TILES_VIDEOS), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, UPLOAD_FOLDER_PROPERTIES_VIDEOS), exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app():
    app = Flask(__name__)
    app.secret_key = FLASK_SECRET_KEY
    app.permanent_session_lifetime = timedelta(hours=6)

    # establish MongoDB connection with a short timeout so the app fails fast
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # trigger a server selection now to raise immediately if unreachable
        client.server_info()
    except Exception as e:
        app.logger.error("MongoDB connection failed: %s", e)
        # rethrow so create_app() doesn't return a running app with no db
        raise

    db = client.get_default_database()

    tiles_col = db.tiles
    properties_col = db.properties
    enquiries_col = db.enquiries

    # ----------------- PUBLIC ROUTES -----------------

    @app.route("/")
    def homepage():
        latest_tiles = list(tiles_col.find().sort("_id", -1).limit(6))
        latest_properties = list(properties_col.find().sort("_id", -1).limit(6))
        return render_template(
            "home.html",
            tiles=latest_tiles,
            properties=latest_properties,
        )

    @app.route("/tiles")
    def tiles_catalog():
        tiles = list(tiles_col.find().sort("_id", -1))
        return render_template("tiles.html", tiles=tiles)

    @app.route("/tiles/<tile_id>")
    def tile_detail(tile_id):
        tile = tiles_col.find_one({"_id": ObjectId(tile_id)})
        if not tile:
            flash("Tile not found", "error")
            return redirect(url_for("tiles_catalog"))
        return render_template("tile_detail.html", tile=tile)

    @app.route("/properties")
    def properties_listing():
        properties = list(properties_col.find().sort("_id", -1))
        return render_template("properties.html", properties=properties)

    @app.route("/properties/<prop_id>")
    def property_detail(prop_id):
        prop = properties_col.find_one({"_id": ObjectId(prop_id)})
        if not prop:
            flash("Property not found", "error")
            return redirect(url_for("properties_listing"))
        return render_template("property_detail.html", prop=prop)

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            phone = request.form.get("phone", "").strip()
            message = request.form.get("message", "").strip()
            if not name or not phone or not message:
                flash("Please fill in all required fields.", "error")
            else:
                enquiries_col.insert_one(
                    {
                        "name": name,
                        "phone": phone,
                        "message": message,
                    }
                )
                flash("Thank you! We will contact you soon.", "success")
                return redirect(url_for("contact"))
        return render_template("contact.html")

    # ----------------- AUTH HELPERS -----------------

    def is_admin():
        return session.get("is_admin") is True

    def require_admin():
        if not is_admin():
            flash("Please log in as admin.", "error")
            return redirect(url_for("admin_login"))
        return None

    # ----------------- ADMIN AUTH -----------------

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")

            admin_user = ADMIN_USERNAME
            admin_pass = ADMIN_PASSWORD

            if username == admin_user and password == admin_pass:
                session.permanent = True
                session["is_admin"] = True
                flash("Logged in successfully.", "success")
                return redirect(url_for("admin_dashboard"))
            flash("Invalid credentials.", "error")
        return render_template("admin_login.html")

    @app.route("/admin/logout")
    def admin_logout():
        session.clear()
        flash("Logged out.", "success")
        return redirect(url_for("homepage"))

    # ----------------- ADMIN DASHBOARD -----------------

    @app.route("/admin")
    def admin_dashboard():
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp
        tiles_count = tiles_col.count_documents({})
        props_count = properties_col.count_documents({})
        enquiries_count = enquiries_col.count_documents({})
        latest_enquiries = list(enquiries_col.find().sort("_id", -1).limit(5))
        return render_template(
            "admin_dashboard.html",
            tiles_count=tiles_count,
            props_count=props_count,
            enquiries_count=enquiries_count,
            latest_enquiries=latest_enquiries,
        )

    # ----------------- ADMIN: TILES CRUD -----------------

    @app.route("/admin/tiles")
    def admin_tiles_list():
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp
        tiles = list(tiles_col.find().sort("_id", -1))
        return render_template("admin_tiles_list.html", tiles=tiles)

    @app.route("/admin/tiles/new", methods=["GET", "POST"])
    def admin_tiles_new():
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp

        if request.method == "POST":
            form = request.form
            images = []
            videos = []
            for file in request.files.getlist("images"):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER_TILES, filename)
                    abs_path = os.path.join(BASE_DIR, save_path)
                    file.save(abs_path)
                    images.append("/" + save_path.replace("\\", "/"))
            for file in request.files.getlist("videos"):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER_TILES_VIDEOS, filename)
                    abs_path = os.path.join(BASE_DIR, save_path)
                    file.save(abs_path)
                    videos.append("/" + save_path.replace("\\", "/"))

            tiles_col.insert_one(
                {
                    "name": form.get("name", "").strip(),
                    "size": form.get("size", "").strip(),
                    "finish": form.get("finish", "").strip(),
                    "price_per_box": float(form.get("price_per_box") or 0),
                    "stock": int(form.get("stock") or 0),
                    "description": form.get("description", "").strip(),
                    "category": form.get("category", "").strip(),
                    "images": images,
                    "videos": videos,
                }
            )
            flash("Tile created.", "success")
            return redirect(url_for("admin_tiles_list"))

        return render_template("admin_tiles_form.html", tile=None)

    @app.route("/admin/tiles/<tile_id>/edit", methods=["GET", "POST"])
    def admin_tiles_edit(tile_id):
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp

        tile = tiles_col.find_one({"_id": ObjectId(tile_id)})
        if not tile:
            flash("Tile not found.", "error")
            return redirect(url_for("admin_tiles_list"))

        if request.method == "POST":
            form = request.form
            images = tile.get("images", [])
            videos = tile.get("videos", [])
            for file in request.files.getlist("images"):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER_TILES, filename)
                    abs_path = os.path.join(BASE_DIR, save_path)
                    file.save(abs_path)
                    images.append("/" + save_path.replace("\\", "/"))
            for file in request.files.getlist("videos"):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER_TILES_VIDEOS, filename)
                    abs_path = os.path.join(BASE_DIR, save_path)
                    file.save(abs_path)
                    videos.append("/" + save_path.replace("\\", "/"))

            tiles_col.update_one(
                {"_id": tile["_id"]},
                {
                    "$set": {
                        "name": form.get("name", "").strip(),
                        "size": form.get("size", "").strip(),
                        "finish": form.get("finish", "").strip(),
                        "price_per_box": float(form.get("price_per_box") or 0),
                        "stock": int(form.get("stock") or 0),
                        "description": form.get("description", "").strip(),
                        "category": form.get("category", "").strip(),
                        "images": images,
                        "videos": videos,
                    }
                },
            )
            flash("Tile updated.", "success")
            return redirect(url_for("admin_tiles_list"))

        return render_template("admin_tiles_form.html", tile=tile)

    @app.route("/admin/tiles/<tile_id>/delete", methods=["POST"])
    def admin_tiles_delete(tile_id):
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp
        tiles_col.delete_one({"_id": ObjectId(tile_id)})
        flash("Tile deleted.", "success")
        return redirect(url_for("admin_tiles_list"))

    # ----------------- ADMIN: PROPERTIES CRUD -----------------

    @app.route("/admin/properties")
    def admin_properties_list():
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp
        properties = list(properties_col.find().sort("_id", -1))
        return render_template("admin_properties_list.html", properties=properties)

    @app.route("/admin/properties/new", methods=["GET", "POST"])
    def admin_properties_new():
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp

        if request.method == "POST":
            form = request.form
            images = []
            videos = []
            for file in request.files.getlist("images"):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER_PROPERTIES, filename)
                    abs_path = os.path.join(BASE_DIR, save_path)
                    file.save(abs_path)
                    images.append("/" + save_path.replace("\\", "/"))
            for file in request.files.getlist("videos"):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER_PROPERTIES_VIDEOS, filename)
                    abs_path = os.path.join(BASE_DIR, save_path)
                    file.save(abs_path)
                    videos.append("/" + save_path.replace("\\", "/"))

            properties_col.insert_one(
                {
                    "title": form.get("title", "").strip(),
                    "location": form.get("location", "").strip(),
                    "price": float(form.get("price") or 0),
                    "square_feet": int(form.get("square_feet") or 0),
                    "property_type": form.get("property_type", "house"),
                    "description": form.get("description", "").strip(),
                    "images": images,
                    "videos": videos,
                }
            )
            flash("Property created.", "success")
            return redirect(url_for("admin_properties_list"))

        return render_template("admin_properties_form.html", prop=None)

    @app.route("/admin/properties/<prop_id>/edit", methods=["GET", "POST"])
    def admin_properties_edit(prop_id):
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp

        prop = properties_col.find_one({"_id": ObjectId(prop_id)})
        if not prop:
            flash("Property not found.", "error")
            return redirect(url_for("admin_properties_list"))

        if request.method == "POST":
            form = request.form
            images = prop.get("images", [])
            videos = prop.get("videos", [])
            for file in request.files.getlist("images"):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER_PROPERTIES, filename)
                    abs_path = os.path.join(BASE_DIR, save_path)
                    file.save(abs_path)
                    images.append("/" + save_path.replace("\\", "/"))
            for file in request.files.getlist("videos"):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(UPLOAD_FOLDER_PROPERTIES_VIDEOS, filename)
                    abs_path = os.path.join(BASE_DIR, save_path)
                    file.save(abs_path)
                    videos.append("/" + save_path.replace("\\", "/"))

            properties_col.update_one(
                {"_id": prop["_id"]},
                {
                    "$set": {
                        "title": form.get("title", "").strip(),
                        "location": form.get("location", "").strip(),
                        "price": float(form.get("price") or 0),
                        "square_feet": int(form.get("square_feet") or 0),
                        "property_type": form.get("property_type", "house"),
                        "description": form.get("description", "").strip(),
                        "images": images,
                        "videos": videos,
                    }
                },
            )
            flash("Property updated.", "success")
            return redirect(url_for("admin_properties_list"))

        return render_template("admin_properties_form.html", prop=prop)

    @app.route("/admin/properties/<prop_id>/delete", methods=["POST"])
    def admin_properties_delete(prop_id):
        redirect_resp = require_admin()
        if redirect_resp:
            return redirect_resp
        properties_col.delete_one({"_id": ObjectId(prop_id)})
        flash("Property deleted.", "success")
        return redirect(url_for("admin_properties_list"))

    return app


if __name__ == "__main__":
    try:
        app = create_app()
    except Exception:
        # if the application failed to initialize (e.g. DB unreachable) bail out
        print("Failed to start application; see logs for details.")
        raise
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

