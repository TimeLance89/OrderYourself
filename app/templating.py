from pathlib import Path
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _num(value):
    if value is None: return ""
    number = float(value)
    if number.is_integer(): return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".").replace(".", ",")


templates.env.filters["num"] = _num
