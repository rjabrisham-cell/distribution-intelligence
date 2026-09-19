from pathlib import Path
from fastapi.templating import Jinja2Templates
from app.core.config import settings

# این فایل داخل app/core/templates.py قرار دارد
# parent => core
# parent.parent => app
APP_DIR = Path(__file__).resolve().parent.parent

# مسیر مطلق پوشه templates
TEMPLATES_DIR = APP_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["map_config"] = settings.public_map_config
