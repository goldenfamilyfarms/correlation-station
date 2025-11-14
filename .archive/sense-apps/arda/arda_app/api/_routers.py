from fastapi import APIRouter

# CID
v1_cid_router = APIRouter(tags=["CID"], prefix="/v1")
v4_cid_router = APIRouter(tags=["CID"], prefix="/v4")
v5_cid_router = APIRouter(tags=["CID"], prefix="/v5")

# ISP
v1_isp_router = APIRouter(tags=["ISP"], prefix="/v1")
v3_isp_router = APIRouter(tags=["ISP"], prefix="/v3")

# Design New
v1_design_router = APIRouter(tags=["Design"], prefix="/v1")

# Design New
v1_design_new_router = APIRouter(tags=["Design New"], prefix="/v1")

# Design MAC
v1_design_mac_router = APIRouter(tags=["Design MAC"], prefix="/v1")

# Remedy
v2_remedy_router = APIRouter(tags=["Remedy"], prefix="/v2")

# Tools
v1_tools_router = APIRouter(tags=["Tools"], prefix="/v1")

# Atlas
atlas_router = APIRouter(tags=["Atlas"], prefix="/atlas")


# Internal - not really meant to be hit directly
v1_internal_router = APIRouter(tags=["Internal"], prefix="/v1")
