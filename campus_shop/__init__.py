import os

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException


def create_app(test_config=None):
    """Create and configure the Campus Mini Shop application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "campus_shop.sqlite"),
        SECRET_KEY=os.environ.get(
            "CAMPUS_SHOP_SECRET_KEY", "dev-only-change-this-secret"
        ),
    )

    if test_config is not None:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    from . import db

    db.init_app(app)

    from . import shop

    app.register_blueprint(shop.bp)
    app.add_template_filter(shop.format_currency, "currency")

    @app.errorhandler(400)
    @app.errorhandler(404)
    def render_http_error(error):
        """Show expected client errors within the normal application shell."""
        if isinstance(error, HTTPException):
            message = error.description
            status_code = error.code
        else:
            message = "The requested page could not be displayed."
            status_code = 500

        return (
            render_template(
                "error.html",
                status_code=status_code,
                message=message,
            ),
            status_code,
        )

    return app
