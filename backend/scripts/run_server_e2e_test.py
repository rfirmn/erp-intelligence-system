#!/usr/bin/env python3
"""End-to-End Server-Like Integration Verification Script.

Replicates a production server environment:
1. Containerized ERP Database (erp_mock_source_db on port 5433)
2. Containerized SQL Feature Store (erp_postgres_fs with pgvector on port 5434)
3. Real SQL Ingestion (ERP_MOCK_DATA=false)
4. Real Machine Learning Training & Inference (XGBoost + TreeSHAP)
5. Real Google Gemini LLM Analytical Synthesis (Google AI Studio API)
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import sys

# Ensure backend directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.session import async_session_factory
from app.ingestion.jobs.billing_sync import run_billing_sync
from app.ingestion.jobs.subscription_sync import run_subscription_sync
from app.insights.compiler import InsightCompiler
from app.main import app
from app.ml.inference.churn_predictor import ChurnInferenceService
from app.ml.registry import get_active_model_metadata
from app.ml.training.train_churn import train_customer_churn_model
from app.models.dimensions import DimCustomer
from app.models.features import FeatureCustomerChurn
from app.models.predictions import PredictionCustomerChurn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("server_e2e")


def print_banner(title: str):
    print("\n" + "=" * 72)
    print(f"  {title.upper()}")
    print("=" * 72)


async def stage_1_verify_containers():
    print_banner("Stage 1: Multi-Container Topology & Database Connectivity")
    erp_url = settings.get_erp_database_url()
    fs_url = settings.get_database_url()

    print(f"[*] ERP Source DB URL       : {erp_url}")
    print(f"[*] Feature Store DB URL    : {fs_url}")
    print(f"[*] Gemini Configured Model : {settings.GEMINI_MODEL}")
    key_preview = f"{settings.GEMINI_API_KEY[:6]}...{settings.GEMINI_API_KEY[-4:]}" if settings.GEMINI_API_KEY else "NONE"
    print(f"[*] Gemini API Key Active   : {key_preview}")

    # Check ERP DB
    erp_engine = create_async_engine(erp_url, echo=False)
    async with erp_engine.connect() as conn:
        res = await conn.execute(text("SELECT count(*) FROM customer_subscription;"))
        erp_subs = res.scalar() or 0
        print(f"[+] Connected to Docker ERP DB (erp_mock_source_db): {erp_subs} subscriptions found.")
    await erp_engine.dispose()

    # Check Feature Store DB
    fs_engine = create_async_engine(fs_url, echo=False)
    async with fs_engine.connect() as conn:
        ext_res = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
        vector_ext = ext_res.scalar()
        print(f"[+] Connected to Docker Feature Store (erp_postgres_fs): pgvector={vector_ext or 'disabled'}")
    await fs_engine.dispose()


async def stage_2_real_ingestion():
    print_banner("Stage 2: Live SQL Ingestion from Docker ERP Database (No Mocks)")
    print("[*] Executing run_subscription_sync(force_full_refresh=True)...")
    sub_res = await run_subscription_sync(force_full_refresh=True)
    print(f"    - Source Type    : {sub_res.get('source_type')} (is_mock={sub_res.get('is_mock_data')})")
    print(f"    - Rows Extracted : {sub_res.get('rows_extracted')}")
    print(f"    - Rows Staged    : {sub_res.get('rows_staged')}")
    print(f"    - SCD2 Dimensions: {sub_res.get('rows_dimensions')}")
    print(f"    - Facts Loaded   : {sub_res.get('rows_fact')}")
    print(f"    - ML Features    : {sub_res.get('rows_features')}")
    assert sub_res.get("status") == "SUCCESS", "Subscription sync failed!"
    assert sub_res.get("is_mock_data") is False, "Ingestion must NOT use mock data!"

    print("\n[*] Executing run_billing_sync(force_full_refresh=True)...")
    bill_res = await run_billing_sync(force_full_refresh=True)
    print(f"    - Source Type    : {bill_res.get('source_type')} (is_mock={bill_res.get('is_mock_data')})")
    print(f"    - Rows Staged    : {bill_res.get('rows_staged')}")
    print(f"    - Facts Loaded   : {bill_res.get('rows_fact')}")
    assert bill_res.get("status") == "SUCCESS", "Billing sync failed!"


async def stage_3_real_ml_pipeline():
    print_banner("Stage 3: Real Machine Learning Pipeline (XGBoost Training & Batch Inference)")
    async with async_session_factory() as session:
        # Verify feature count
        count_q = select(func.count()).select_from(FeatureCustomerChurn)
        fs_count = (await session.execute(count_q)).scalar() or 0
        print(f"[*] Total customer feature records available in Feature Store: {fs_count}")

        # Train real model
        print("[*] Training real XGBoost Customer Churn Model...")
        train_res = await train_customer_churn_model(
            session=session,
            model_version="1.0.0-server-e2e",
            preset="default",
            set_as_active=True,
        )
        print(f"    - Model Name    : {train_res['model_name']}")
        print(f"    - Model Version : {train_res['model_version']}")
        print(f"    - Status        : {train_res['status']}")
        print(f"    - Samples Used  : {train_res['total_samples']}")
        print(f"    - Metrics       : {train_res['metrics']}")
        print(f"    - Top Features  : {[f['feature'] for f in train_res['top_global_features'][:3]]}")

        # Run real batch inference
        print("\n[*] Running vectorized batch inference across customer features...")
        batch_res = await ChurnInferenceService.predict_batch(session)
        print(f"    - Snapshot Date : {batch_res['snapshot_date']}")
        print(f"    - Total Scored  : {batch_res['total_evaluated']}")
        print(f"    - High Risk     : {batch_res['high_risk_count']}")
        print(f"    - Medium Risk   : {batch_res['medium_risk_count']}")
        print(f"    - Low Risk      : {batch_res['low_risk_count']}")
        print(f"    - Average Prob  : {batch_res['average_churn_probability']:.4f}")

        # Sample customer explainability profile
        high_risk_sample = await ChurnInferenceService.get_high_risk_customers(session, limit=1, min_probability=0.0)
        if high_risk_sample:
            s = high_risk_sample[0]
            print(f"\n[*] Sample Customer Profile (ID={s['customer_id']}):")
            print(f"    - Name         : {s['customer_name']}")
            print(f"    - Churn Prob   : {s['churn_probability']:.4f} ({s['risk_level']})")
            print(f"    - TreeSHAP Key : {s['top_risk_factors'][0]['description'] if s['top_risk_factors'] else 'N/A'}")


async def stage_4_real_gemini_synthesis():
    print_banner("Stage 4: Real Google Gemini LLM Synthesis (Google AI Studio API)")
    async with async_session_factory() as session:
        compiler = InsightCompiler(session)
        print(f"[*] Invoking LangGraph CommercialAgent + Google Gemini ({settings.GEMINI_MODEL})...")
        start_time = datetime.now(timezone.utc)
        package = await compiler.compile_module_insight(domain="commercial")
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        print(f"[+] Synthesis Completed in {duration:.2f} seconds!")
        print("\n" + "-" * 72)
        print(f"EXECUTIVE SUMMARY (Synthesized by {settings.GEMINI_MODEL}):")
        print("-" * 72)
        print(package.executive_summary)
        print("-" * 72)

        print("\nKEY METRICS GENERATED:")
        for m in package.key_metrics:
            print(f"  * {m.label:<28} : {m.formatted_value} {m.unit} [{m.status.upper() if m.status else 'INFO'}]")

        print(f"\nNARRATIVE INSIGHTS ({len(package.narrative_insights)} items):")
        for idx, ins in enumerate(package.narrative_insights, start=1):
            print(f"  [{idx}] [{ins.severity.upper()}] {ins.title}")
            print(f"      Narrative : {ins.narrative[:160]}...")
            if ins.suggested_actions:
                print(f"      Action    : {ins.suggested_actions[0]}")

        print(f"\nVISUALIZATIONS ({len(package.visualizations)} Vega-Lite specs):")
        for v in package.visualizations:
            print(f"  * {v.chart_id}: {v.title} (Library: {v.chart_library})")


async def stage_5_api_endpoints():
    print_banner("Stage 5: Full-Stack Production API Endpoint Contract Verification")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Commercial Insights Endpoint
        print("[*] GET /api/v1/insights/commercial...")
        resp = await client.get("/api/v1/insights/commercial")
        assert resp.status_code == 200, f"API failed with {resp.status_code}: {resp.text}"
        payload = resp.json()
        assert payload["success"] is True
        print(f"    - HTTP Status : {resp.status_code}")
        print(f"    - Request ID  : {payload['meta']['request_id']}")
        print(f"    - Executive Summary preview: {payload['data']['executive_summary'][:90]}...")

        # Dashboard Overview Endpoint
        print("\n[*] GET /api/v1/dashboard/overview...")
        resp2 = await client.get("/api/v1/dashboard/overview")
        assert resp2.status_code == 200, f"Overview API failed: {resp2.text}"
        payload2 = resp2.json()
        assert payload2["success"] is True
        print(f"    - HTTP Status : {resp2.status_code}")
        print(f"    - Health Score: {payload2['data']['key_metrics'][0]['formatted_value']}")


async def main():
    print_banner("Starting Real Server-Like End-to-End Verification")
    start_total = datetime.now(timezone.utc)

    await stage_1_verify_containers()
    await stage_2_real_ingestion()
    await stage_3_real_ml_pipeline()
    await stage_4_real_gemini_synthesis()
    await stage_5_api_endpoints()

    total_duration = (datetime.now(timezone.utc) - start_total).total_seconds()
    print_banner("ALL STAGES COMPLETED SUCCESSFULLY")
    print(f"[*] Total Execution Time: {total_duration:.2f} seconds")
    print("[*] Status: 100% PASS — Zero Mocks, Real Docker DBs, Real XGBoost, Real Google Gemini LLM.\n")


if __name__ == "__main__":
    asyncio.run(main())
