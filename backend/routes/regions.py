from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from backend.models.schemas import RegionResponse, RegionCreate, ErrorResponse
from backend.services.region_service import (
    get_all_regions,
    get_region_by_id,
    create_region
)
from backend.utils.logger import logger

router = APIRouter(prefix="/regions", tags=["Regions"])


@router.get("", response_model=List[RegionResponse])
def list_regions(active_only: bool = True, db: Session = Depends(get_db)):
    """
    Returns the list of monitored regions (coordinates and metadata).
    Does NOT return fake AQI data.
    """
    regions = get_all_regions(db, active_only=active_only)
    return regions


@router.get(
    "/{region_id}",
    response_model=RegionResponse,
    responses={404: {"model": ErrorResponse, "description": "Region not found"}}
)
def get_region(region_id: int, db: Session = Depends(get_db)):
    """
    Returns information for a specific region by its identifier.
    """
    region = get_region_by_id(db, region_id)
    if not region:
        logger.warning(f"Region lookup failed: region_id={region_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region with id {region_id} does not exist."
        )
    return region


@router.post(
    "",
    response_model=RegionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse, "description": "Region already exists or invalid"}}
)
def add_region(region_in: RegionCreate, db: Session = Depends(get_db)):
    """
    Registers a new geographic region for monitoring.
    """
    try:
        new_region = create_region(db, region_in)
        return new_region
    except ValueError as ve:
        logger.warning(f"Failed to add region: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error creating region: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the region."
        )
