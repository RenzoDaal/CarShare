import os
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import SQLModel

router = APIRouter(tags=["routing"])

ORS_API_KEY = os.environ.get("ORS_API_KEY")
ORS_BASE_URL = "https://api.openrouteservice.org"

if not ORS_API_KEY:
    raise RuntimeError("ORS_API_KEY environment variable is not set")


class RouteEstimateRequest(SQLModel):
    stops: List[str]


class RouteEstimateResponse(SQLModel):
    distance_km: float
    coordinates: List[List[float]]


@router.get("/locations/suggest", response_model=List[str])
async def suggest_locations(query: str = Query(..., min_length=3)):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                f"{ORS_BASE_URL}/geocode/search",
                params={
                    "api_key": ORS_API_KEY,
                    "text": query,
                    "size": 5,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Error talking to geocoding service: {e}",
            )

        data = resp.json()
        features = data.get("features", [])
        suggestions: List[str] = []
        for feature in features:
            label = feature.get("properties", {}).get("label")
            if label:
                suggestions.append(label)

        return suggestions


@router.post("/routes/estimate", response_model=RouteEstimateResponse)
async def estimate_route(body: RouteEstimateRequest):
    if len(body.stops) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two stops (start and end) are required.",
        )

    async with httpx.AsyncClient(timeout=15) as client:
        coords: List[List[float]] = []
        for address in body.stops:
            try:
                geo_resp = await client.get(
                    f"{ORS_BASE_URL}/geocode/search",
                    params={
                        "api_key": ORS_API_KEY,
                        "text": address,
                        "size": 1,
                    },
                )
                geo_resp.raise_for_status()
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"Geocoding failed for '{address}': {e}",
                )

            features = geo_resp.json().get("features", [])
            if not features:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not find coordinates for address '{address}'.",
                )

            lon, lat = features[0]["geometry"]["coordinates"]
            coords.append([lon, lat])

        try:
            route_resp = await client.post(
                f"{ORS_BASE_URL}/v2/directions/driving-car/geojson",
                params={"api_key": ORS_API_KEY},
                json={"coordinates": coords},
                headers={"Content-Type": "application/json"},
            )
            route_resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Routing request failed: {e}",
            )

        data = route_resp.json()

        # GeoJSON FeatureCollection -> first feature is the route
        # docs: /v2/directions/{profile}/geojson :contentReference[oaicite:0]{index=0}
        features = data.get("features", [])
        if not features:
            raise HTTPException(
                status_code=500,
                detail="No route features returned from routing service.",
            )

        feature = features[0]
        props = feature.get("properties", {})
        summary = props.get("summary", {})
        distance_m = summary.get("distance", 0.0)
        distance_km = distance_m / 1000.0

        geometry = feature.get("geometry", {})
        coordinates_lonlat = geometry.get("coordinates", [])  # [[lon, lat], ...]

        return RouteEstimateResponse(
            distance_km=distance_km,
            coordinates=coordinates_lonlat,
        )
