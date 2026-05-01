"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    StockAI - Health Check Page                               ║
║              Production monitoring endpoint for Docker/K8s                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Run with: streamlit run ui/healthcheck.py --server.port 8511
"""

import streamlit as st
import os
import sys
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_imports() -> dict:
    """Check that all critical imports work."""
    checks = {}
    
    try:
        from ui.simulation_engine import SimulationEngine
        checks["simulation_engine"] = True
    except Exception as e:
        checks["simulation_engine"] = str(e)
    
    try:
        from record import BatchRecordManager
        checks["record_manager"] = True
    except Exception as e:
        checks["record_manager"] = str(e)
    
    try:
        from utils.rate_limiter import RateLimiter
        checks["rate_limiter"] = True
    except Exception as e:
        checks["rate_limiter"] = str(e)
    
    return checks


def check_environment() -> dict:
    """Check environment configuration."""
    return {
        "GROQ_API_KEY": "✅ Set" if os.getenv("GROQ_API_KEY") else "❌ Not set",
        "GOOGLE_API_KEY": "✅ Set" if os.getenv("GOOGLE_API_KEY") else "❌ Not set",
        "OPENAI_API_KEY": "✅ Set" if os.getenv("OPENAI_API_KEY") else "❌ Not set",
    }


def main():
    st.set_page_config(
        page_title="StockAI Health Check",
        page_icon="🏥",
        layout="centered"
    )
    
    st.title("🏥 StockAI Health Check")
    st.caption(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Overall status
    import_checks = check_imports()
    all_imports_ok = all(v is True for v in import_checks.values())
    
    if all_imports_ok:
        st.success("✅ **System Healthy** - All critical imports working")
    else:
        st.error("❌ **System Unhealthy** - Some imports failed")
    
    # Import checks
    st.subheader("📦 Module Imports")
    for module, status in import_checks.items():
        if status is True:
            st.markdown(f"- ✅ `{module}`")
        else:
            st.markdown(f"- ❌ `{module}`: {status}")
    
    # Environment checks
    st.subheader("🔑 Environment Variables")
    env_checks = check_environment()
    for var, status in env_checks.items():
        st.markdown(f"- {status} `{var}`")
    
    # Memory usage (if psutil available)
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        st.subheader("💾 Memory Usage")
        st.metric("Current Memory", f"{memory_mb:.1f} MB")
    except ImportError:
        pass
    
    # API response for monitoring tools
    st.subheader("📡 API Response")
    response = {
        "status": "healthy" if all_imports_ok else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "imports": {k: "ok" if v is True else "error" for k, v in import_checks.items()},
    }
    st.json(response)


if __name__ == "__main__":
    main()
