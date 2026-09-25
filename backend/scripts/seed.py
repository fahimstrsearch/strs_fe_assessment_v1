"""Seed markets, training properties and their analyst reference underwritings.

Idempotent: re-running upserts the markets and properties and replaces each
reference underwriting. Trainee attempts and submissions are left untouched.

    uv run python -m scripts.seed
    uv run python -m scripts.seed --reset   # wipe every seeded row first
    uv run python -m scripts.seed --if-empty  # no-op once properties exist
"""

import asyncio
import sys
from decimal import Decimal

from sqlalchemy import delete, func, select, text

from app.core.database import AsyncSessionLocal
from app.models import Market, Property, Underwriting
from app.repositories.property_repository import PropertyRepository
from app.repositories.underwriting_repository import UnderwritingRepository
from app.schemas.underwriting import (
    CompSetInput,
    DealTagsInput,
    ForecastedRevenueInput,
    OperatingExpenseInput,
    OptimizationItemInput,
    PurchaseDetailsInput,
    SaveUnderwritingPayload,
    UnderwritingTaxInput,
)
from app.services.underwriting_service import UnderwritingService

D = Decimal

STANDARD_TAXES = UnderwritingTaxInput(
    land_assumptions_pct=D("0.20"),
    sla_multiplier_pct=D("0.25"),
    bonus_amount_pct=D("0.60"),
    tax_rate_pct=D("0.37"),
)


def _purchase(price: str, rate="0.0699", down="0.20", closing="0.03", years=30):
    return PurchaseDetailsInput(
        purchase_price=D(price),
        down_payment_pct=D(down),
        interest_rate=D(rate),
        mortgage_years=years,
        closing_costs_pct=D(closing),
    )


def _revenue(low: str, mid: str, high: str, cohost="0.0", appreciation="0.03"):
    return ForecastedRevenueInput(
        co_hosting_fee_pct=D(cohost),
        annual_re_appreciation_pct=D(appreciation),
        scenarios={
            "low": {"forecasted_revenue": D(low)},
            "mid": {"forecasted_revenue": D(mid)},
            "high": {"forecasted_revenue": D(high)},
        },
    )


def _opex(**monthly: str):
    return [
        OperatingExpenseInput(
            expense_name=name.replace("_", " ").title(), monthly_amount=D(v)
        )
        for name, v in monthly.items()
    ]


def _opt(*items: tuple[str, str]):
    return [OptimizationItemInput(category=c, total_price=D(p)) for c, p in items]


def _comps(*rows: tuple[str, str, int, int]):
    return [
        CompSetInput(listing_url=url, revenue=D(rev), bedrooms=bd, sleeps=sl)
        for url, rev, bd, sl in rows
    ]


# Each property below references one of these by slug.
MARKETS: list[dict] = [
    dict(
        slug="smoky-blue-ridge-mountains",
        name="Smoky & Blue Ridge Mountains",
        state=None,
        region="Southern Appalachia",
        timezone="America/New_York",
        description=(
            "Drive-to cabin market spanning the Tennessee Smokies and the north "
            "Georgia mountains. Year-round demand; views and hot tubs carry ADR."
        ),
    ),
    dict(
        slug="broken-bow",
        name="Broken Bow",
        state="OK",
        region="Ouachita Mountains",
        timezone="America/Chicago",
        description=(
            "Hochatown / Broken Bow luxury cabin market fed by DFW and OKC. "
            "New-build heavy, light regulation, weekend-weighted occupancy."
        ),
    ),
    dict(
        slug="central-florida",
        name="Central Florida",
        state="FL",
        region="Orlando Metro",
        timezone="America/New_York",
        description=(
            "Theme-park resort communities around Kissimmee and Davenport. Large "
            "themed homes, HOA-governed, cohost-friendly, steady year-round."
        ),
    ),
    dict(
        slug="texas-gulf-coast",
        name="Texas Gulf Coast",
        state="TX",
        region="Coastal Bend",
        timezone="America/Chicago",
        description=(
            "Port Aransas and Mustang Island beach market. Heavy summer "
            "seasonality and windstorm insurance, offset by top-decile peak ADR."
        ),
    ),
]

SEED: list[tuple[dict, SaveUnderwritingPayload]] = [
    (
        dict(
            zpid="41234567",
            market="smoky-blue-ridge-mountains",
            address="1240 Ski View Dr, Gatlinburg, TN 37738",
            address_street="1240 Ski View Dr",
            address_city="Gatlinburg",
            address_state="TN",
            address_zipcode="37738",
            price="$675,000",
            unformatted_price="675000",
            beds=3,
            baths=3.0,
            area=2150,
            latitude=35.7143,
            longitude=-83.5102,
            home_type="SINGLE_FAMILY",
            home_status="FOR_SALE",
            time_on_zillow="12 days",
            img_src="https://picsum.photos/seed/gatlinburg/640/420",
            detail_url="https://www.zillow.com/homedetails/1240-Ski-View-Dr/41234567_zpid/",
        ),
        SaveUnderwritingPayload(
            bedrooms=3,
            bathrooms=D("3.0"),
            sleep_count_low=8,
            sleep_count_high=10,
            purchase_details=_purchase("660000"),
            forecasted_revenue=_revenue("105000", "125000", "142000"),
            taxes=STANDARD_TAXES,
            optimization_items=_opt(
                ("Furniture & design", "45000"),
                ("Hot tub", "12000"),
                ("Game room", "9000"),
            ),
            operating_expenses=_opex(
                utilities="450",
                internet="90",
                insurance="320",
                property_taxes="410",
                lawn_and_snow="120",
                supplies="150",
                software="60",
                maintenance_reserve="250",
            ),
            comp_set=_comps(
                ("https://www.airbnb.com/rooms/1001", "118000", 3, 9),
                ("https://www.airbnb.com/rooms/1002", "131000", 3, 10),
                ("https://www.airbnb.com/rooms/1003", "109500", 3, 8),
            ),
            tags=DealTagsInput(
                furnished=False,
                luxury=False,
                add_inground_pool=False,
                renovation_level=2,
                deal_complexity=2,
            ),
            deal_pitch="Mountain-view cabin near Ober; strong year-round demand.",
        ),
    ),
    (
        dict(
            zpid="52345678",
            market="broken-bow",
            address="88 Lakeshore Ln, Broken Bow, OK 74728",
            address_street="88 Lakeshore Ln",
            address_city="Broken Bow",
            address_state="OK",
            address_zipcode="74728",
            price="$540,000",
            unformatted_price="540000",
            beds=2,
            baths=2.0,
            area=1600,
            latitude=34.1324,
            longitude=-94.7405,
            home_type="SINGLE_FAMILY",
            home_status="FOR_SALE",
            time_on_zillow="5 days",
            img_src="https://picsum.photos/seed/brokenbow/640/420",
            detail_url="https://www.zillow.com/homedetails/88-Lakeshore-Ln/52345678_zpid/",
        ),
        SaveUnderwritingPayload(
            bedrooms=2,
            bathrooms=D("2.0"),
            sleep_count_low=6,
            sleep_count_high=8,
            purchase_details=_purchase("525000", down="0.25"),
            forecasted_revenue=_revenue("82000", "96000", "108000"),
            taxes=STANDARD_TAXES,
            optimization_items=_opt(
                ("Furniture & design", "38000"), ("Hot tub", "11000")
            ),
            operating_expenses=_opex(
                utilities="380",
                internet="85",
                insurance="260",
                property_taxes="330",
                lawn="100",
                supplies="120",
                software="60",
                maintenance_reserve="200",
            ),
            comp_set=_comps(
                ("https://www.airbnb.com/rooms/2001", "94000", 2, 6),
                ("https://www.airbnb.com/rooms/2002", "101000", 2, 8),
            ),
            tags=DealTagsInput(
                new_construction=True, renovation_level=1, deal_complexity=1
            ),
            deal_pitch="New-build luxury cabin in Hochatown; turnkey.",
        ),
    ),
    (
        dict(
            zpid="63456789",
            market="central-florida",
            address="3402 Palm Isle Ct, Kissimmee, FL 34747",
            address_street="3402 Palm Isle Ct",
            address_city="Kissimmee",
            address_state="FL",
            address_zipcode="34747",
            price="$895,000",
            unformatted_price="895000",
            beds=6,
            baths=5.5,
            area=3400,
            latitude=28.3200,
            longitude=-81.6100,
            home_type="SINGLE_FAMILY",
            home_status="FOR_SALE",
            time_on_zillow="27 days",
            img_src="https://picsum.photos/seed/kissimmee/640/420",
            detail_url="https://www.zillow.com/homedetails/3402-Palm-Isle-Ct/63456789_zpid/",
        ),
        SaveUnderwritingPayload(
            bedrooms=6,
            bathrooms=D("5.5"),
            sleep_count_low=14,
            sleep_count_high=16,
            purchase_details=_purchase("870000"),
            forecasted_revenue=_revenue("140000", "165000", "185000", cohost="0.10"),
            taxes=STANDARD_TAXES,
            optimization_items=_opt(
                ("Furniture & design", "70000"),
                ("Themed bedrooms", "25000"),
                ("Pool heater & screen", "9000"),
                ("Game room", "15000"),
            ),
            operating_expenses=_opex(
                utilities="700",
                internet="100",
                insurance="520",
                property_taxes="900",
                hoa="380",
                pool_service="180",
                lawn="140",
                supplies="220",
                software="60",
                maintenance_reserve="350",
            ),
            comp_set=_comps(
                ("https://www.airbnb.com/rooms/3001", "158000", 6, 14),
                ("https://www.airbnb.com/rooms/3002", "172000", 6, 16),
                ("https://www.airbnb.com/rooms/3003", "149000", 5, 12),
            ),
            tags=DealTagsInput(
                add_inground_pool=False,
                luxury=True,
                can_support_cohost=True,
                renovation_level=3,
                deal_complexity=3,
            ),
            deal_pitch="Large themed home near Disney; pool already in.",
        ),
    ),
    (
        dict(
            zpid="74567890",
            market="smoky-blue-ridge-mountains",
            address="215 Aspen Ridge Rd, Blue Ridge, GA 30513",
            address_street="215 Aspen Ridge Rd",
            address_city="Blue Ridge",
            address_state="GA",
            address_zipcode="30513",
            price="$725,000",
            unformatted_price="725000",
            beds=4,
            baths=3.5,
            area=2600,
            latitude=34.8640,
            longitude=-84.3240,
            home_type="SINGLE_FAMILY",
            home_status="FOR_SALE",
            time_on_zillow="41 days",
            img_src="https://picsum.photos/seed/blueridge/640/420",
            detail_url="https://www.zillow.com/homedetails/215-Aspen-Ridge-Rd/74567890_zpid/",
        ),
        SaveUnderwritingPayload(
            bedrooms=4,
            bathrooms=D("3.5"),
            sleep_count_low=10,
            sleep_count_high=12,
            purchase_details=_purchase("690000"),
            forecasted_revenue=_revenue("110000", "128000", "145000"),
            taxes=STANDARD_TAXES,
            optimization_items=_opt(
                ("Furniture & design", "52000"),
                ("Hot tub", "12000"),
                ("Fire pit & deck", "8000"),
            ),
            operating_expenses=_opex(
                utilities="480",
                internet="90",
                insurance="340",
                property_taxes="450",
                lawn="120",
                supplies="160",
                software="60",
                maintenance_reserve="260",
            ),
            comp_set=_comps(
                ("https://www.airbnb.com/rooms/4001", "121000", 4, 10),
                ("https://www.airbnb.com/rooms/4002", "136000", 4, 12),
            ),
            tags=DealTagsInput(
                waterfront=False, remote=True, renovation_level=2, deal_complexity=2
            ),
            deal_pitch="Long-range mountain views, 41 DOM gives negotiation room.",
        ),
    ),
    (
        dict(
            zpid="85678901",
            market="texas-gulf-coast",
            address="9 Dune Walk, Port Aransas, TX 78373",
            address_street="9 Dune Walk",
            address_city="Port Aransas",
            address_state="TX",
            address_zipcode="78373",
            price="$1,150,000",
            unformatted_price="1150000",
            beds=5,
            baths=4.0,
            area=2900,
            latitude=27.8339,
            longitude=-97.0611,
            home_type="SINGLE_FAMILY",
            home_status="FOR_SALE",
            time_on_zillow="9 days",
            img_src="https://picsum.photos/seed/portaransas/640/420",
            detail_url="https://www.zillow.com/homedetails/9-Dune-Walk/85678901_zpid/",
        ),
        SaveUnderwritingPayload(
            bedrooms=5,
            bathrooms=D("4.0"),
            sleep_count_low=12,
            sleep_count_high=14,
            purchase_details=_purchase("1125000", down="0.25"),
            forecasted_revenue=_revenue("165000", "192000", "215000"),
            taxes=STANDARD_TAXES,
            optimization_items=_opt(
                ("Furniture & design", "65000"),
                ("Private pool", "75000"),
                ("Golf cart", "9000"),
            ),
            operating_expenses=_opex(
                utilities="650",
                internet="100",
                insurance="1100",
                property_taxes="1500",
                hoa="250",
                pool_service="170",
                lawn="120",
                supplies="220",
                software="60",
                maintenance_reserve="400",
            ),
            comp_set=_comps(
                ("https://www.airbnb.com/rooms/5001", "188000", 5, 12),
                ("https://www.airbnb.com/rooms/5002", "205000", 5, 14),
                ("https://www.airbnb.com/rooms/5003", "176000", 4, 12),
            ),
            tags=DealTagsInput(
                waterfront=True,
                add_inground_pool=True,
                luxury=True,
                renovation_level=3,
                deal_complexity=4,
            ),
            deal_pitch="Beach walk-over; pool add unlocks top-decile revenue.",
        ),
    ),
    (
        dict(
            zpid="96789012",
            market="smoky-blue-ridge-mountains",
            address="47 Cedar Hollow Rd, Sevierville, TN 37876",
            address_street="47 Cedar Hollow Rd",
            address_city="Sevierville",
            address_state="TN",
            address_zipcode="37876",
            price="$449,000",
            unformatted_price="449000",
            beds=2,
            baths=2.0,
            area=1350,
            latitude=35.8681,
            longitude=-83.5619,
            home_type="SINGLE_FAMILY",
            home_status="FOR_SALE",
            time_on_zillow="3 days",
            img_src="https://picsum.photos/seed/sevierville/640/420",
            detail_url="https://www.zillow.com/homedetails/47-Cedar-Hollow-Rd/96789012_zpid/",
        ),
        SaveUnderwritingPayload(
            bedrooms=2,
            bathrooms=D("2.0"),
            sleep_count_low=6,
            sleep_count_high=6,
            purchase_details=_purchase("440000"),
            forecasted_revenue=_revenue("68000", "80000", "91000"),
            taxes=STANDARD_TAXES,
            optimization_items=_opt(
                ("Furniture & design", "32000"), ("Hot tub", "11000")
            ),
            operating_expenses=_opex(
                utilities="350",
                internet="85",
                insurance="230",
                property_taxes="260",
                lawn="90",
                supplies="110",
                software="60",
                maintenance_reserve="180",
            ),
            comp_set=_comps(
                ("https://www.airbnb.com/rooms/6001", "77000", 2, 6),
                ("https://www.airbnb.com/rooms/6002", "84000", 2, 6),
            ),
            tags=DealTagsInput(
                existing_airbnb=True,
                furnished=True,
                turnkey=True,
                renovation_level=1,
                deal_complexity=1,
            ),
            deal_pitch="Existing Airbnb with bookings on the calendar; starter deal.",
        ),
    ),
]


async def _wipe(db) -> None:
    """Drop every seeded row, including trainee work, so seeding starts clean.

    TRUNCATE rather than DELETE so ids restart at 1 on every reset and the
    seeded markets keep stable, quotable ids.
    """
    await db.execute(
        text(
            "TRUNCATE TABLE training_submissions, underwritings, properties, "
            "markets RESTART IDENTITY CASCADE"
        )
    )
    await db.commit()
    print("wiped submissions, underwritings, properties and markets")


async def _seed_markets(db) -> dict[str, Market]:
    by_slug: dict[str, Market] = {}
    for data in MARKETS:
        market = await db.scalar(select(Market).where(Market.slug == data["slug"]))
        if market is None:
            market = Market(**data)
            db.add(market)
        else:
            for k, v in data.items():
                setattr(market, k, v)
        by_slug[data["slug"]] = market
    await db.flush()
    print(f"seeded {len(by_slug)} markets: {', '.join(sorted(by_slug))}")
    return by_slug


async def seed(*, reset: bool = False, if_empty: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        if reset:
            await _wipe(db)
        elif if_empty and await db.scalar(select(func.count()).select_from(Property)):
            print("database already seeded, skipping")
            return

        markets = await _seed_markets(db)

        prop_repo = PropertyRepository(db)
        uw_repo = UnderwritingRepository(db)
        service = UnderwritingService(uw_repo, prop_repo)

        for prop_data, reference_payload in SEED:
            prop_data = dict(prop_data)
            market = markets[prop_data.pop("market")]
            prop_data["market_id"] = market.id

            prop = await db.get(Property, prop_data["zpid"])
            if prop is None:
                prop = Property(**prop_data)
                db.add(prop)
            else:
                for k, v in prop_data.items():
                    setattr(prop, k, v)
            await db.flush()

            existing = await db.scalar(
                select(Underwriting.id).where(
                    Underwriting.zpid == prop.zpid, Underwriting.is_reference.is_(True)
                )
            )
            if existing is not None:
                await db.execute(
                    delete(Underwriting).where(Underwriting.id == existing)
                )
                await db.flush()

            started = await service.start(prop.zpid)
            row = await uw_repo.get_by_id(started.id)
            service._apply_payload(row, reference_payload)
            service._recalculate(row)
            row.is_reference = True
            row.market_id = market.id
            row.deal_status = "training_deal"
            row.source = "reference"
            await db.commit()
            print(
                f"seeded {prop.zpid} {prop.address} "
                f"[{market.name}] -> reference uw #{row.id}"
            )


if __name__ == "__main__":
    asyncio.run(seed(reset="--reset" in sys.argv, if_empty="--if-empty" in sys.argv))
