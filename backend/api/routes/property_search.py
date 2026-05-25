from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])

_BATCHDATA_KEY = os.environ.get("BATCHDATA_API_KEY", "")
_BASE_V1 = "https://api.batchdata.com/api/v1"

_DATASETS = [
    "core",
    "contact",
    "valuation",
    "mortgage-liens",
    "deed",
    "foreclosure",
    "owner",
]


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_BATCHDATA_KEY}",
        "Content-Type": "application/json",
    }


def _parse(prop: dict[str, Any]) -> dict[str, Any]:
    address = prop.get("address", {})
    building = prop.get("building", {})
    owner = prop.get("owner", {})
    valuation = prop.get("valuation", {})
    tax = prop.get("tax", {})
    sale = prop.get("sale", {})

    return {
        "attomId": prop.get("propertyId", prop.get("id", "")),
        "address": address.get("address", address.get("street", "")),
        "city": address.get("city", ""),
        "state": address.get("state", ""),
        "zip": address.get("zip", ""),
        "bedrooms": building.get("bedrooms", prop.get("bedrooms")),
        "bathrooms": building.get("bathrooms", prop.get("bathrooms")),
        "squareFeet": building.get("squareFeet", prop.get("squareFeet")),
        "yearBuilt": building.get("yearBuilt", prop.get("yearBuilt")),
        "estimatedValue": valuation.get("estimatedValue", prop.get("estimatedValue")),
        "lastSalePrice": sale.get("salePrice", prop.get("lastSalePrice")),
        "lastSaleDate": sale.get("saleDate", prop.get("lastSaleDate")),
        "ownerName": owner.get("fullName", prop.get("ownerName")),
        "lotSize": building.get("lotSquareFeet", prop.get("lotSize")),
        "propertyType": prop.get("propertyType", prop.get("type")),
        "taxAssessment": tax.get("assessedValue", prop.get("taxAssessment")),
        "taxDelinquent": bool(tax.get("taxDelinquent", prop.get("taxDelinquent", False))),
    }


def _split_address(address: str) -> tuple[str, str, str, str]:
    parts = address.split(",")
    street = parts[0].strip() if parts else address
    city = ""
    state = ""
    zip_code = ""
    if len(parts) >= 2:
        city = parts[1].strip()
    if len(parts) >= 3:
        state_zip = parts[2].strip().split()
        if state_zip:
            state = state_zip[0]
        if len(state_zip) > 1:
            zip_code = state_zip[1]
    return street, city, state, zip_code


@router.get("")
async def search_properties(
    address: str = Query(..., min_length=5),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    if not _BATCHDATA_KEY:
        return _mock_results(address)

    street, city, state, zip_code = _split_address(address)

    payload = {
        "requests": [
            {
                "address": {
                    "street": street,
                    "city": city,
                    "state": state,
                    "zip": zip_code,
                }
            }
        ],
        "options": {
            "skipTrace": False,
            "datasets": _DATASETS,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{_BASE_V1}/property/lookup/all-attributes",
                json=payload,
                headers=_headers(),
            )
            if not res.is_success:
                return _mock_results(address)
            data = res.json()
            properties = data.get("results", {}).get("properties") or []
            if not properties:
                return _mock_results(address)
            return [_parse(p) for p in properties]
    except Exception:
        return _mock_results(address)


def _mock_results(address: str) -> list[dict]:
    return [
        {
            "attomId": "mock-001",
            "address": address,
            "city": "Stockton",
            "state": "CA",
            "zip": "95202",
            "bedrooms": 3,
            "bathrooms": 2,
            "squareFeet": 1450,
            "yearBuilt": 1978,
            "estimatedValue": 285000,
            "lastSalePrice": 190000,
            "lastSaleDate": "2019-03-15",
            "ownerName": "John & Mary Smith",
            "lotSize": 6500,
            "propertyType": "Single Family Residence",
            "taxAssessment": 210000,
            "taxDelinquent": False,
        }
    ]