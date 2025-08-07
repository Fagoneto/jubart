from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/market", response_class=HTMLResponse)
async def market_page(request: Request, tipo: str = "impo"):
    return templates.TemplateResponse("market.html", {
        "request": request,
        "tipo": tipo
    })
