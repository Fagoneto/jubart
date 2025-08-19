# app/routes/pages.py
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates  # <-- use fastapi.templating

templates = Jinja2Templates(directory="templates")
router = APIRouter()

@router.get("/paineis/comercio-exterior")
def pagina_comex(request: Request):
    # Seu index.html está em app/templates/index.html
    return templates.TemplateResponse("index.html", {"request": request})
