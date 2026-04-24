from __future__ import annotations

from fastapi import APIRouter, Depends

from app.domain.models import IoTemplate


def get_manager():
    from app.main import manager

    return manager


router = APIRouter(prefix="/api/io-templates", tags=["io-templates"])


@router.get("")
def list_templates(mgr=Depends(get_manager)):
    return mgr.list_templates()


@router.post("")
def create_template(template: IoTemplate, mgr=Depends(get_manager)):
    return mgr.upsert_template(template)


@router.put("/{template_id}")
def update_template(template_id: str, template: IoTemplate, mgr=Depends(get_manager)):
    template.templateId = template_id
    return mgr.upsert_template(template)

