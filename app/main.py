# app/main.py - COMPLETE FIXED VERSION

import os
import sys
import logging
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4

# FastAPI imports
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# UPDATED IMPORT - Enterprise RAG Service
try:
    from app.services.enhanced_rag_service import EnterpriseRAGService
    RAG_SERVICE_AVAILABLE = True
except ImportError:
    print("⚠️ Enterprise RAG Service not found - AI features will use fallback mode")
    RAG_SERVICE_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Global metrics storage for observability
METRICS_STORE = {
    'api_requests_total': 0,
    'ai_queries_total': 0,
    'response_time_sum': 0.0,
    'errors_total': 0,
    'active_users': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'database_queries': 0,
    'gemini_api_calls': 0,
    'start_time': datetime.utcnow(),
    'requests_by_hour': {},
    'error_types': {},
    'popular_queries': {},
    'response_times': [],
    'security_blocks': 0,
    'validation_failures': 0,
    'gemini_tokens_used': 0,
    'gemini_input_tokens': 0,
    'gemini_output_tokens': 0
}

def update_metrics(metric_name: str, value: Any = 1):
    """Update metrics with thread safety considerations"""
    global METRICS_STORE
    
    if metric_name in ['api_requests_total', 'ai_queries_total', 'errors_total', 'cache_hits', 
                       'cache_misses', 'database_queries', 'gemini_api_calls', 'security_blocks', 
                       'validation_failures', 'gemini_tokens_used', 'gemini_input_tokens', 'gemini_output_tokens']:
        METRICS_STORE[metric_name] += value
    elif metric_name == 'response_time_sum':
        METRICS_STORE[metric_name] += value
        METRICS_STORE['response_times'].append(value)
        # Keep only last 1000 response times
        if len(METRICS_STORE['response_times']) > 1000:
            METRICS_STORE['response_times'] = METRICS_STORE['response_times'][-1000:]
    elif metric_name == 'active_users':
        METRICS_STORE['active_users'] = max(METRICS_STORE['active_users'], value)
    
    # Track requests by hour for trend analysis
    current_hour = datetime.utcnow().strftime('%Y-%m-%d %H:00')
    if current_hour not in METRICS_STORE['requests_by_hour']:
        METRICS_STORE['requests_by_hour'][current_hour] = 0
    METRICS_STORE['requests_by_hour'][current_hour] += 1
    
    # Cleanup old hourly data (keep last 48 hours)
    if len(METRICS_STORE['requests_by_hour']) > 48:
        sorted_hours = sorted(METRICS_STORE['requests_by_hour'].keys())
        for old_hour in sorted_hours[:-48]:
            del METRICS_STORE['requests_by_hour'][old_hour]

# Enhanced Pydantic Models with Enterprise Features
class QuestionRequest(BaseModel):
    """Request model for AI questions with enhanced validation"""
    question: str = Field(..., min_length=1, max_length=2000, description="User's question about cloud costs")
    context: Optional[str] = Field(None, max_length=500, description="Additional context for the question")
    
    @validator('question')
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        
        # Basic security validation
        suspicious_patterns = [
            'ignore', 'system:', 'assistant:', 'prompt:', 'instructions:',
            '<script>', 'javascript:', 'DROP TABLE', 'DELETE FROM',
            'rm -rf', '../', 'passwd', 'sudo'
        ]
        
        v_lower = v.lower()
        for pattern in suspicious_patterns:
            if pattern.lower() in v_lower:
                raise ValueError(f'Question contains potentially harmful content: {pattern}')
        
        return v.strip()

class KPIRequest(BaseModel):
    """Request model for KPI queries with enhanced filtering"""
    month: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}$', description="Month in YYYY-MM format")
    service: Optional[str] = Field(None, max_length=100, description="Filter by specific service")
    resource_group: Optional[str] = Field(None, max_length=100, description="Filter by resource group")
    min_cost: Optional[float] = Field(None, ge=0, description="Minimum cost filter")

class HealthResponse(BaseModel):
    """Comprehensive health check response model"""
    status: str
    service: str
    version: str
    timestamp: str
    uptime_seconds: float
    database_status: str
    ai_service_status: str
    total_records: int
    system_load: Dict[str, Any]
    feature_flags: Dict[str, bool]

class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0

class AIResponse(BaseModel):
    """Enhanced AI response model with comprehensive enterprise features"""
    answer: str
    sources: List[str] = Field(default_factory=list, description="Knowledge sources used")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score (0-1)")
    processing_time: float = Field(description="Processing time in seconds")
    data_available: bool = Field(description="Whether database data was available")
    request_id: str = Field(description="Unique request identifier")
    
    # Enterprise features
    visualization_data: Optional[Dict[str, Any]] = Field(None, description="Data for charts and visualizations")
    key_metrics: Optional[Dict[str, Any]] = Field(None, description="Key performance indicators")
    insights_summary: str = Field(default="", description="Executive summary of insights")
    query_classification: str = Field(default="general", description="Type of query processed")
    data_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Quality of underlying data")
    business_impact: str = Field(default="", description="Business impact assessment")
    token_usage: TokenUsage = Field(default_factory=TokenUsage, description="AI token usage statistics")

    
    # Enterprise features
    visualization_data: Optional[Dict[str, Any]] = Field(None, description="Data for charts and visualizations")
    key_metrics: Optional[Dict[str, Any]] = Field(None, description="Key performance indicators")
    insights_summary: str = Field(default="", description="Executive summary of insights")
    query_classification: str = Field(default="general", description="Type of query processed")
    data_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Quality of underlying data")
    business_impact: str = Field(default="", description="Business impact assessment")
    token_usage: Dict[str, Any] = Field(default_factory=dict, description="AI token usage statistics")

class KPIResponse(BaseModel):
    """Enhanced KPI response model with comprehensive metrics"""
    monthly_total: float
    resource_count: int
    service_count: int
    resource_group_count: int
    service_breakdown: Dict[str, float]
    resource_group_breakdown: Dict[str, float]
    trend_data: List[Dict[str, Any]]
    top_resources: List[Dict[str, Any]]
    cost_efficiency_metrics: Dict[str, float]
    month_filter: Optional[str] = None
    generated_at: str

class RecommendationResponse(BaseModel):
    """Enhanced recommendations response model"""
    recommendations: List[Dict[str, Any]]
    summary: Dict[str, Any]
    total_potential_savings: float
    priority_breakdown: Dict[str, int]
    generated_at: str
    analysis_period: str
    request_id: str

class MetricsResponse(BaseModel):
    """Comprehensive metrics response model for observability"""
    uptime_hours: float
    total_requests: int
    ai_queries: int
    error_rate: float
    avg_response_time: float
    active_users: int
    database_queries: int
    gemini_api_calls: int
    cache_hit_rate: float
    security_blocks: int
    validation_failures: int
    requests_per_hour: Dict[str, int]
    recent_response_times: List[float]
    system_health: str
    error_breakdown: Dict[str, int]
    performance_stats: Dict[str, float]
    token_usage: Dict[str, int]

# Initialize FastAPI app with comprehensive configuration
app = FastAPI(
    title="AI Cost & Insights Copilot",
    description="Enterprise-grade FinOps analytics platform with AI-powered natural language querying, comprehensive observability, and advanced security features.",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
rag_service: Optional[EnterpriseRAGService] = None
DB_PATH = "data/app.db"

def get_db_connection():
    """Get database connection with metrics tracking and error handling"""
    try:
        update_metrics('database_queries')
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")

def get_db_stats():
    """Get comprehensive database statistics"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get billing record count
            cursor.execute("SELECT COUNT(*) FROM billing")
            billing_count = cursor.fetchone()[0]
            
            # Get resource count
            cursor.execute("SELECT COUNT(*) FROM resources")
            resource_count = cursor.fetchone()[0]
            
            # Get date range
            cursor.execute("SELECT MIN(invoice_month), MAX(invoice_month) FROM billing")
            date_range = cursor.fetchone()
            
            return {
                'billing_records': billing_count,
                'resource_records': resource_count,
                'date_range': {
                    'start': date_range[0],
                    'end': date_range[1]
                }
            }
    except Exception as e:
        logger.error(f"Error getting DB stats: {e}")
        return {
            'billing_records': 0,
            'resource_records': 0,
            'date_range': {'start': None, 'end': None}
        }

def add_security_headers(response: JSONResponse) -> JSONResponse:
    """Add security headers to response"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Comprehensive request middleware for tracking, security, and observability"""
    start_time = time.time()
    request_id = str(uuid4())
    
    # Track request
    update_metrics('api_requests_total')
    
    # Log request
    logger.info(f"[{request_id}] {request.method} {request.url.path} - User-Agent: {request.headers.get('user-agent', 'Unknown')}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Update metrics
        update_metrics('response_time_sum', process_time)
        
        # Add headers
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        response.headers["X-Request-ID"] = request_id
        
        # Add security headers
        response = add_security_headers(response)
        
        # Log successful response
        logger.info(f"[{request_id}] Response: {response.status_code} in {process_time:.4f}s")
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        update_metrics('errors_total')
        
        # Track error types
        error_type = type(e).__name__
        if error_type not in METRICS_STORE['error_types']:
            METRICS_STORE['error_types'][error_type] = 0
        METRICS_STORE['error_types'][error_type] += 1
        
        logger.error(f"[{request_id}] Request failed after {process_time:.4f}s: {type(e).__name__}: {str(e)}")
        raise

@app.on_event("startup")
async def startup_event():
    """Initialize services and perform startup checks"""
    global rag_service
    
    logger.info("🚀 Starting AI Cost & Insights Copilot v2.1...")
    
    # Initialize Enterprise RAG service
    if RAG_SERVICE_AVAILABLE:
        try:
            rag_service = EnterpriseRAGService()
            logger.info("✅ Enterprise RAG Service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Enterprise RAG service: {e}")
            rag_service = None
    else:
        logger.warning("⚠️ Enterprise RAG Service not available - AI features will use fallback mode")
    
    # Verify database connectivity and structure
    try:
        db_stats = get_db_stats()
        if db_stats['billing_records'] > 0:
            logger.info(f"✅ Database connected: {db_stats['billing_records']} billing records, "
                       f"{db_stats['resource_records']} resources, "
                       f"Date range: {db_stats['date_range']['start']} to {db_stats['date_range']['end']}")
        else:
            logger.warning("⚠️ Database connected but no billing records found")
    except Exception as e:
        logger.error(f"❌ Database connectivity check failed: {e}")
    
    # Initialize metrics
    METRICS_STORE['start_time'] = datetime.utcnow()
    
    # Verify required environment variables
    required_env_vars = ['GOOGLE_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.warning(f"⚠️ Missing environment variables: {missing_vars} - Some features may be limited")
    
    logger.info("🎉 Application startup completed successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 AI Cost & Insights Copilot shutting down...")
    
    # Log final metrics
    uptime = (datetime.utcnow() - METRICS_STORE['start_time']).total_seconds()
    logger.info(f"📊 Final metrics: {METRICS_STORE['api_requests_total']} requests, "
               f"{METRICS_STORE['ai_queries_total']} AI queries, "
               f"{uptime:.1f}s uptime")

# API Endpoints

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with comprehensive service information and status"""
    uptime = (datetime.utcnow() - METRICS_STORE['start_time']).total_seconds()
    db_stats = get_db_stats()
    
    return {
        "service": "AI Cost & Insights Copilot",
        "version": "2.1.0",
        "description": "Enterprise-grade FinOps analytics platform with AI-powered natural language querying",
        "status": "running",
        "uptime_seconds": round(uptime, 1),
        "features": {
            "enterprise_rag_service": rag_service is not None,
            "database_connectivity": db_stats['billing_records'] > 0,
            "comprehensive_observability": True,
            "advanced_security": True,
            "detailed_cost_breakdowns": True,
            "trend_analysis": True,
            "optimization_recommendations": True,
            "governance_insights": True
        },
        "data_summary": {
            "billing_records": db_stats['billing_records'],
            "resource_records": db_stats['resource_records'],
            "date_range": db_stats['date_range']
        },
        "endpoints": {
            "health": "/health - Comprehensive system health check",
            "kpi": "/api/kpi - Enhanced key performance indicators",
            "ask": "/api/ask - Enterprise AI-powered question answering",
            "recommendations": "/api/recommendations - Advanced cost optimization suggestions",
            "metrics": "/api/metrics - System observability and performance metrics",
            "analytics": "/api/analytics - Usage analytics and insights",
            "docs": "/docs - Interactive API documentation",
            "redoc": "/redoc - Alternative API documentation"
        },
        "current_metrics": {
            "total_requests": METRICS_STORE['api_requests_total'],
            "ai_queries": METRICS_STORE['ai_queries_total'],
            "error_rate": round((METRICS_STORE['errors_total'] / max(METRICS_STORE['api_requests_total'], 1)) * 100, 2),
            "avg_response_time_ms": round((METRICS_STORE['response_time_sum'] / max(METRICS_STORE['api_requests_total'], 1)) * 1000, 2)
        },
        "enterprise_capabilities": {
            "detailed_cost_analysis": "Service and resource group breakdowns with percentages and trends",
            "trend_analysis": "Month-over-month comparisons with variance analysis and business context",
            "optimization_insights": "Idle resource detection with savings estimates and prioritization",
            "governance_analysis": "Tagging compliance analysis and cost allocation insights",
            "executive_summaries": "KPI tracking with business impact assessment",
            "visualization_data": "Chart and table data for comprehensive dashboards",
            "security_features": "Input validation, prompt injection protection, and security monitoring",
            "observability": "Structured logging, metrics collection, and performance monitoring"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check with detailed system status"""
    request_id = str(uuid4())
    
    try:
        logger.info(f"[{request_id}] Performing comprehensive health check")
        
        start_time = METRICS_STORE['start_time']
        uptime = (datetime.utcnow() - start_time).total_seconds()
        
        # Database health check
        db_stats = get_db_stats()
        db_status = "healthy" if db_stats['billing_records'] > 0 else "no_data" if db_stats['billing_records'] == 0 else "error"
        
        # AI service health check
        ai_status = "available" if rag_service else "unavailable"
        if rag_service and hasattr(rag_service, 'gemini_model'):
            ai_status = "available_with_gemini" if rag_service.gemini_model else "available_fallback"
        
        # System load metrics
        total_requests = METRICS_STORE['api_requests_total']
        error_rate = (METRICS_STORE['errors_total'] / max(total_requests, 1)) * 100
        
        system_load = {
            "requests_per_minute": len([t for t in METRICS_STORE['response_times'] if t < 60]),
            "error_rate_percent": round(error_rate, 2),
            "avg_response_time_ms": round((METRICS_STORE['response_time_sum'] / max(total_requests, 1)) * 1000, 2),
            "memory_usage": "monitoring_not_implemented",  # Would implement with psutil
            "cpu_usage": "monitoring_not_implemented"
        }
        
        # Feature flags
        feature_flags = {
            "enterprise_rag": rag_service is not None,
            "gemini_ai": rag_service and hasattr(rag_service, 'gemini_model') and rag_service.gemini_model is not None,
            "vector_search": rag_service and hasattr(rag_service, 'vector_store') and rag_service.vector_store is not None,
            "comprehensive_analytics": True,
            "security_monitoring": True,
            "performance_tracking": True
        }
        
        overall_status = "healthy"
        if db_status == "error" or error_rate > 20:
            overall_status = "critical"
        elif db_status == "no_data" or error_rate > 10 or not rag_service:
            overall_status = "degraded"
        
        logger.info(f"[{request_id}] Health check completed: {overall_status}")
        
        return HealthResponse(
            status=overall_status,
            service="AI Cost & Insights Copilot",
            version="2.1.0",
            timestamp=datetime.utcnow().isoformat(),
            uptime_seconds=uptime,
            database_status=db_status,
            ai_service_status=ai_status,
            total_records=db_stats['billing_records'],
            system_load=system_load,
            feature_flags=feature_flags
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.get("/api/kpi", response_model=KPIResponse)
async def get_kpi(request: KPIRequest = Depends()):
    """Get enhanced KPI metrics with comprehensive analytics and filtering"""
    request_id = str(uuid4())
    
    try:
        logger.info(f"[{request_id}] KPI request: month={request.month}, service={request.service}, resource_group={request.resource_group}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic query with filters
            where_conditions = []
            params = []
            
            if request.month:
                where_conditions.append("invoice_month = ?")
                params.append(request.month)
            
            if request.service:
                where_conditions.append("service = ?")
                params.append(request.service)
            
            if request.resource_group:
                where_conditions.append("resource_group = ?")
                params.append(request.resource_group)
            
            if request.min_cost:
                where_conditions.append("cost >= ?")
                params.append(request.min_cost)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Get comprehensive metrics
            metrics_query = f"""
            SELECT 
                SUM(cost) as total_cost,
                COUNT(DISTINCT resource_id) as resource_count,
                COUNT(DISTINCT service) as service_count,
                COUNT(DISTINCT resource_group) as resource_group_count,
                AVG(cost) as avg_cost,
                MIN(cost) as min_cost,
                MAX(cost) as max_cost,
                SUM(usage_qty) as total_usage,
                AVG(usage_qty) as avg_usage,
                AVG(unit_cost) as avg_unit_cost
            FROM billing 
            WHERE {where_clause}
            """
            
            cursor.execute(metrics_query, params)
            metrics = cursor.fetchone()
            
            monthly_total = float(metrics[0] or 0)
            resource_count = int(metrics[1] or 0)
            service_count = int(metrics[2] or 0)
            resource_group_count = int(metrics[3] or 0)
            
            # Cost efficiency metrics
            cost_efficiency_metrics = {
                'avg_cost_per_resource': float(metrics[4] or 0),
                'min_cost': float(metrics[5] or 0),
                'max_cost': float(metrics[6] or 0),
                'total_usage': float(metrics[7] or 0),
                'avg_usage_per_resource': float(metrics[8] or 0),
                'avg_unit_cost': float(metrics[9] or 0),
                'cost_distribution_ratio': float(metrics[6] / max(metrics[5], 1) if metrics[5] and metrics[6] else 0)
            }
            
            # Enhanced service breakdown
            service_query = f"""
            SELECT 
                service, 
                SUM(cost) as total_cost,
                COUNT(DISTINCT resource_id) as resource_count,
                AVG(cost) as avg_cost,
                ROUND((SUM(cost) * 100.0 / (SELECT SUM(cost) FROM billing WHERE {where_clause})), 2) as percentage
            FROM billing 
            WHERE {where_clause}
            GROUP BY service
            ORDER BY total_cost DESC
            """
            cursor.execute(service_query, params * 2)  # Double params for subquery
            services = cursor.fetchall()
            service_breakdown = {row[0]: float(row[1]) for row in services}
            
            # Enhanced resource group breakdown
            rg_query = f"""
            SELECT 
                resource_group, 
                SUM(cost) as total_cost,
                COUNT(DISTINCT resource_id) as resource_count,
                COUNT(DISTINCT service) as service_count,
                ROUND((SUM(cost) * 100.0 / (SELECT SUM(cost) FROM billing WHERE {where_clause})), 2) as percentage
            FROM billing 
            WHERE {where_clause}
            GROUP BY resource_group
            ORDER BY total_cost DESC
            LIMIT 15
            """
            cursor.execute(rg_query, params * 2)
            rgs = cursor.fetchall()
            resource_group_breakdown = {row[0]: float(row[1]) for row in rgs}
            
            # Get trend data (last 6 months)
            trend_query = """
            SELECT 
                invoice_month, 
                SUM(cost) as total_cost, 
                COUNT(DISTINCT resource_id) as resources,
                COUNT(DISTINCT service) as services,
                AVG(cost) as avg_cost
            FROM billing
            GROUP BY invoice_month
            ORDER BY invoice_month DESC
            LIMIT 6
            """
            cursor.execute(trend_query)
            trends = cursor.fetchall()
            trend_data = [
                {
                    'invoice_month': row[0], 
                    'total_cost': float(row[1]),
                    'resource_count': int(row[2]),
                    'service_count': int(row[3]),
                    'avg_cost_per_resource': float(row[4] or 0),
                    'month_name': f"{['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(row[0].split('-')[1])]} {row[0].split('-')[0]}"
                }
                for row in reversed(trends)
            ]
            
            # Get top resources with enhanced details
            resources_query = f"""
            SELECT 
                resource_id, 
                service, 
                resource_group,
                SUM(cost) as total_cost, 
                AVG(usage_qty) as avg_usage,
                COUNT(*) as billing_records,
                AVG(unit_cost) as avg_unit_cost,
                MAX(cost) as max_single_cost
            FROM billing 
            WHERE {where_clause}
            GROUP BY resource_id, service, resource_group
            ORDER BY total_cost DESC
            LIMIT 15
            """
            cursor.execute(resources_query, params)
            resources = cursor.fetchall()
            top_resources = [
                {
                    'resource_id': row[0],
                    'resource_name': row[0].split('/')[-1] if '/' in row[0] else row[0][:30],
                    'service': row[1],
                    'resource_group': row[2],
                    'total_cost': float(row[3]),
                    'avg_usage': float(row[4] or 0),
                    'billing_records': int(row[5]),
                    'avg_unit_cost': float(row[6] or 0),
                    'max_single_cost': float(row[7] or 0),
                    'cost_efficiency': float(row[3] / max(row[4] or 1, 1))  # Cost per usage unit
                }
                for row in resources
            ]
        
        logger.info(f"[{request_id}] KPI response generated: ${monthly_total:,.2f}, {resource_count} resources, {service_count} services")
        
        return KPIResponse(
            monthly_total=monthly_total,
            resource_count=resource_count,
            service_count=service_count,
            resource_group_count=resource_group_count,
            service_breakdown=service_breakdown,
            resource_group_breakdown=resource_group_breakdown,
            trend_data=trend_data,
            top_resources=top_resources,
            cost_efficiency_metrics=cost_efficiency_metrics,
            month_filter=request.month,
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        update_metrics('errors_total')
        logger.error(f"[{request_id}] KPI request failed: {e}")
        raise HTTPException(status_code=500, detail=f"KPI request failed: {str(e)}")

@app.post("/api/ask", response_model=AIResponse)
async def ask_question(request: QuestionRequest):
    """Enterprise AI-powered question answering with comprehensive analysis and security"""
    request_id = str(uuid4())
    start_time = time.time()
    
    try:
        update_metrics('ai_queries_total')
        logger.info(f"[{request_id}] Enterprise AI question received: {request.question[:100]}...")
        
        # Track popular queries for analytics
        question_key = request.question.lower()[:50]
        if question_key not in METRICS_STORE['popular_queries']:
            METRICS_STORE['popular_queries'][question_key] = 0
        METRICS_STORE['popular_queries'][question_key] += 1
        
        # Initialize token tracking for this request
        token_usage = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'estimated_cost': 0.0
        }
        
        # Enhanced fallback when AI service unavailable
        if not rag_service:
            processing_time = time.time() - start_time
            logger.warning(f"[{request_id}] AI service unavailable, using enhanced fallback")
            
            return AIResponse(
                answer=f"""## ⚠️ Enterprise AI Service Status

I apologize, but the enterprise AI analysis service is currently unavailable. However, I can provide you with alternative approaches:

**For your question:** "{request.question}"

**Available alternatives:**
1. **KPI Dashboard**: Use `/api/kpi` endpoint for detailed cost metrics and breakdowns
2. **Recommendations**: Check `/api/recommendations` for optimization insights  
3. **Direct Database Queries**: Access billing data directly for specific cost information
4. **System Status**: Monitor `/health` endpoint for service restoration updates

**When the enterprise service is restored, you'll get:**
- Comprehensive cost analysis with exact figures from your database
- Detailed service and resource group breakdowns with percentages
- Month-over-month trend analysis with business insights
- Optimization recommendations with estimated savings
- Executive summaries with actionable next steps
- Interactive visualization data for dashboards

**Troubleshooting:**
- The service may be initializing if recently started
- Check that all required dependencies are installed
- Verify environment configuration (GOOGLE_API_KEY, etc.)
- Contact your administrator for enterprise RAG service setup""",
                sources=["System fallback mode - Enterprise RAG service unavailable"],
                recommendations=[
                    "Check system health at /health endpoint for detailed service status",
                    "Use /api/kpi endpoint for basic cost metrics and breakdowns",
                    "Monitor logs for service initialization messages",
                    "Verify enterprise RAG service configuration and dependencies"
                ],
                confidence=0.1,
                processing_time=processing_time,
                data_available=False,
                request_id=request_id,
                visualization_data={},
                key_metrics={},
                insights_summary="Enterprise AI service unavailable - using fallback mode",
                query_classification="service_unavailable",
                data_quality_score=0.0,
                business_impact="Limited analysis capabilities until enterprise service is restored",
                token_usage=token_usage
            )
        
        # Enterprise RAG processing
        logger.info(f"[{request_id}] Processing with Enterprise RAG Service...")
        
        try:
            response_data = await rag_service.ask_question(request.question)
        except Exception as rag_error:
            logger.error(f"[{request_id}] Enterprise RAG processing failed: {rag_error}")
            # Fallback to basic response
            response_data = {
                "answer": f"I encountered an issue while processing your question: {str(rag_error)}. Please try rephrasing your question or contact support.",
                "sources": [],
                "recommendations": ["Try rephrasing your question", "Check system status", "Contact support"],
                "confidence": 0.0,
                "processing_time": 0,
                "data_available": False,
                "visualization_data": {},
                "key_metrics": {},
                "insights_summary": f"Processing error: {str(rag_error)}",
                "query_classification": "error"
            }
        
        processing_time = time.time() - start_time
        
        # Track Gemini API usage
        if hasattr(rag_service, 'gemini_model') and rag_service.gemini_model:
            update_metrics('gemini_api_calls')
            
            # Estimate token usage (approximate)
            question_tokens = len(request.question.split()) * 1.3  # Rough tokenization
            response_tokens = len(response_data.get('answer', '').split()) * 1.3
            
            token_usage = {
                'input_tokens': int(question_tokens),
                'output_tokens': int(response_tokens),
                'total_tokens': int(question_tokens + response_tokens),
                'estimated_cost': round(question_tokens + response_tokens)  # $0.005 per 1K tokens
            }
            
            # Update global token metrics
            update_metrics('gemini_input_tokens', token_usage['input_tokens'])
            update_metrics('gemini_output_tokens', token_usage['output_tokens'])
            update_metrics('gemini_tokens_used', token_usage['total_tokens'])
        
        # Calculate data quality score
        data_quality_score = 0.8 if response_data.get('data_available') else 0.1
        if response_data.get('key_metrics', {}).get('total_cost', 0) > 0:
            data_quality_score += 0.2
        
        # Assess business impact
        business_impact = "Standard cost analysis"
        if response_data.get('key_metrics', {}).get('potential_savings', 0) > 1000:
            business_impact = "High-impact optimization opportunity identified"
        elif response_data.get('query_classification') == 'trend_analysis':
            business_impact = "Cost trend analysis for strategic planning"
        
        logger.info(f"[{request_id}] Enterprise AI response generated in {processing_time:.2f}s, "
                   f"confidence: {response_data.get('confidence', 0):.2f}, "
                   f"classification: {response_data.get('query_classification', 'unknown')}")
        
        return AIResponse(
            answer=response_data.get('answer', 'No response generated'),
            sources=response_data.get('sources', []),
            recommendations=response_data.get('recommendations', []),
            confidence=response_data.get('confidence', 0.5),
            processing_time=processing_time,
            data_available=response_data.get('data_available', False),
            request_id=request_id,
            visualization_data=response_data.get('visualization_data', {}),
            key_metrics=response_data.get('key_metrics', {}),
            insights_summary=response_data.get('insights_summary', ''),
            query_classification=response_data.get('query_classification', 'general'),
            data_quality_score=data_quality_score,
            business_impact=business_impact,
            token_usage=token_usage
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        update_metrics('errors_total')
        
        logger.error(f"[{request_id}] Enterprise AI question failed after {processing_time:.2f}s: {type(e).__name__}: {str(e)}")
        
        return AIResponse(
            answer=f"""## ❌ Error Processing Your Question

I encountered an unexpected error while analyzing: "{request.question}"

**Error Details:** {type(e).__name__}: {str(e)}

**Troubleshooting Steps:**
1. **Data Availability**: Ensure your database contains billing data for the requested period
2. **Question Format**: Try asking about a specific month (e.g., "August 2024 costs")  
3. **Simplify Query**: Focus on one aspect - costs, services, or resource groups
4. **System Status**: Check `/health` endpoint for overall system status
5. **Database Schema**: Verify the database schema matches expected format

**Alternative Questions to Try:**
- "What was the total spend last month?"
- "Show me costs breakdown by service"
- "Which resources are most expensive?"
- "How did costs change from July to August?"

**Support Information:**
- Request ID: {request_id}
- Processing Time: {processing_time:.2f}s  
- Error Type: {type(e).__name__}

The system continues to learn and improve from these interactions to provide better responses in the future.""",
            sources=["Error handling system"],
            recommendations=[
                "Verify your question format and try rephrasing more specifically",
                "Check database connectivity and data availability using /health endpoint", 
                f"Contact support with Request ID: {request_id} if the issue persists",
                "Try asking about a different time period or using simpler query terms"
            ],
            confidence=0.0,
            processing_time=processing_time,
            data_available=False,
            request_id=request_id,
            visualization_data={},
            key_metrics={},
            insights_summary=f"Processing error: {type(e).__name__}: {str(e)[:100]}...",
            query_classification="error",
            data_quality_score=0.0,
            business_impact="Unable to assess due to processing error",
            token_usage={'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'estimated_cost': 0.0}
        )

@app.get("/api/recommendations", response_model=RecommendationResponse)
async def get_recommendations():
    """Get comprehensive cost optimization recommendations with detailed analysis"""
    request_id = str(uuid4())
    
    try:
        logger.info(f"[{request_id}] Generating comprehensive cost optimization recommendations")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get latest month for analysis
            cursor.execute("SELECT MAX(invoice_month) FROM billing")
            latest_month = cursor.fetchone()[0]
            
            if not latest_month:
                return RecommendationResponse(
                    recommendations=[],
                    summary={"message": "No billing data available for analysis"},
                    total_potential_savings=0.0,
                    priority_breakdown={"high": 0, "medium": 0, "low": 0},
                    generated_at=datetime.utcnow().isoformat(),
                    analysis_period="No data",
                    request_id=request_id
                )
            
            logger.info(f"[{request_id}] Analyzing data for period: {latest_month}")
            
            recommendations = []
            total_estimated_savings = 0.0
            priority_counts = {"high": 0, "medium": 0, "low": 0}
            
            # 1. IDLE/UNDERUTILIZED RESOURCES ANALYSIS
            idle_query = """
            SELECT 
                resource_id,
                service,
                resource_group,
                SUM(cost) as monthly_cost,
                AVG(usage_qty) as avg_usage,
                COUNT(*) as usage_records,
                MIN(usage_qty) as min_usage,
                MAX(usage_qty) as max_usage,
                AVG(unit_cost) as avg_unit_cost
            FROM billing 
            WHERE invoice_month = ?
            AND cost > 5  -- Focus on resources costing more than $5/month
            GROUP BY resource_id, service, resource_group
            HAVING AVG(usage_qty) < 10 AND COUNT(*) >= 3  -- Low usage with sufficient data points
            ORDER BY monthly_cost DESC
            LIMIT 20
            """
            
            cursor.execute(idle_query, (latest_month,))
            idle_resources = cursor.fetchall()
            
            for resource in idle_resources:
                resource_id, service, resource_group, monthly_cost, avg_usage, usage_records, min_usage, max_usage, avg_unit_cost = resource
                
                # Calculate utilization rate and savings potential
                utilization_rate = (avg_usage / 100) * 100 if avg_usage > 0 else 0  # Assuming 100 is full utilization
                
                if utilization_rate < 5:
                    # Very low utilization - recommend termination
                    estimated_savings = monthly_cost * 0.90  # 90% savings
                    priority = "high"
                    recommendation_text = "Terminate this severely underutilized resource"
                elif utilization_rate < 20:
                    # Low utilization - recommend rightsizing
                    estimated_savings = monthly_cost * 0.60  # 60% savings
                    priority = "high" if monthly_cost > 100 else "medium"
                    recommendation_text = "Rightsize to a smaller instance or tier"
                else:
                    # Moderate underutilization - recommend monitoring
                    estimated_savings = monthly_cost * 0.30  # 30% savings
                    priority = "medium"
                    recommendation_text = "Monitor usage patterns and consider optimization"
                
                total_estimated_savings += estimated_savings
                priority_counts[priority] += 1
                
                recommendations.append({
                    'type': 'idle_resource',
                    'priority': priority,
                    'resource_id': resource_id,
                    'resource_name': resource_id.split('/')[-1] if '/' in resource_id else resource_id,
                    'service': service,
                    'resource_group': resource_group,
                    'current_cost': float(monthly_cost),
                    'estimated_savings': float(estimated_savings),
                    'utilization_rate': round(utilization_rate, 1),
                    'avg_usage': float(avg_usage),
                    'usage_records': int(usage_records),
                    'usage_range': f"{float(min_usage):.1f} - {float(max_usage):.1f}",
                    'description': f'Underutilized resource with {utilization_rate:.1f}% utilization rate',
                    'recommendation': recommendation_text,
                    'confidence': 0.9 if usage_records > 10 else 0.7,
                    'monthly_impact': float(estimated_savings),
                    'annual_impact': float(estimated_savings * 12)
                })
            
            # 2. TAGGING GAPS ANALYSIS
            tagging_query = """
            SELECT 
                b.resource_id,
                b.service,
                b.resource_group,
                SUM(b.cost) as monthly_cost,
                CASE 
                    WHEN r.owner IS NULL OR r.owner = '' THEN 'missing_owner'
                    WHEN r.env IS NULL OR r.env = '' THEN 'missing_environment' 
                    ELSE 'missing_other'
                END as missing_tag_type
            FROM billing b
            LEFT JOIN resources r ON b.resource_id = r.resource_id
            WHERE b.invoice_month = ?
            AND (r.owner IS NULL OR r.owner = '' OR r.env IS NULL OR r.env = '' OR r.tags_json IS NULL OR r.tags_json = '')
            AND b.cost > 2
            GROUP BY b.resource_id, b.service, b.resource_group, missing_tag_type
            ORDER BY monthly_cost DESC
            LIMIT 25
            """
            
            cursor.execute(tagging_query, (latest_month,))
            untagged_resources = cursor.fetchall()
            
            for resource in untagged_resources:
                resource_id, service, resource_group, monthly_cost, missing_tag_type = resource
                
                priority = "high" if monthly_cost > 50 else "medium"
                priority_counts[priority] += 1
                
                recommendations.append({
                    'type': 'tagging_gap',
                    'priority': priority,
                    'resource_id': resource_id,
                    'resource_name': resource_id.split('/')[-1] if '/' in resource_id else resource_id,
                    'service': service,
                    'resource_group': resource_group,
                    'current_cost': float(monthly_cost),
                    'estimated_savings': 0.0,  # Indirect savings through better governance
                    'missing_tag_type': missing_tag_type,
                    'description': f'Missing {missing_tag_type.replace("_", " ")} affecting cost allocation',
                    'recommendation': f'Add proper {missing_tag_type.replace("_", " ")} tags for cost governance',
                    'confidence': 0.95,
                    'governance_impact': 'Improves cost allocation and accountability',
                    'compliance_risk': 'Medium' if monthly_cost > 25 else 'Low'
                })
            
            # 3. HIGH-COST RESOURCE REVIEW
            high_cost_query = """
            SELECT 
                resource_id,
                service,
                resource_group,
                SUM(cost) as monthly_cost,
                AVG(unit_cost) as avg_unit_cost,
                COUNT(DISTINCT invoice_month) as months_active,
                MAX(cost) as max_single_cost,
                MIN(cost) as min_single_cost
            FROM billing 
            WHERE invoice_month = ?
            AND cost > 200  -- High-cost threshold
            GROUP BY resource_id, service, resource_group
            ORDER BY monthly_cost DESC
            LIMIT 15
            """
            
            cursor.execute(high_cost_query, (latest_month,))
            high_cost_resources = cursor.fetchall()
            
            for resource in high_cost_resources:
                resource_id, service, resource_group, monthly_cost, avg_unit_cost, months_active, max_cost, min_cost = resource
                
                # Calculate potential savings through reserved instances or optimization
                cost_variability = (max_cost - min_cost) / max_cost if max_cost > 0 else 0
                
                if monthly_cost > 1000:
                    estimated_savings = monthly_cost * 0.30  # 30% through reserved instances
                    priority = "high"
                elif monthly_cost > 500:
                    estimated_savings = monthly_cost * 0.20  # 20% savings
                    priority = "medium"
                else:
                    estimated_savings = monthly_cost * 0.15  # 15% savings
                    priority = "medium"
                
                total_estimated_savings += estimated_savings
                priority_counts[priority] += 1
                
                recommendations.append({
                    'type': 'high_cost_review',
                    'priority': priority,
                    'resource_id': resource_id,
                    'resource_name': resource_id.split('/')[-1] if '/' in resource_id else resource_id,
                    'service': service,
                    'resource_group': resource_group,
                    'current_cost': float(monthly_cost),
                    'estimated_savings': float(estimated_savings),
                    'cost_variability': round(cost_variability * 100, 1),
                    'avg_unit_cost': float(avg_unit_cost),
                    'description': f'High-cost resource requiring optimization review (${monthly_cost:,.2f}/month)',
                    'recommendation': 'Consider reserved instances, alternative configurations, or architectural changes',
                    'confidence': 0.75,
                    'optimization_options': [
                        'Reserved instance pricing' if monthly_cost > 500 else None,
                        'Instance type optimization',
                        'Usage pattern analysis',
                        'Alternative service evaluation'
                    ],
                    'potential_ri_savings': float(monthly_cost * 0.35) if monthly_cost > 500 else 0
                })
            
            # Sort recommendations by estimated savings
            recommendations.sort(key=lambda x: x.get('estimated_savings', 0), reverse=True)
            
            # Create comprehensive summary
            summary = {
                'analysis_period': latest_month,
                'total_recommendations': len(recommendations),
                'priority_breakdown': priority_counts,
                'category_breakdown': {
                    'idle_resources': len([r for r in recommendations if r['type'] == 'idle_resource']),
                    'tagging_gaps': len([r for r in recommendations if r['type'] == 'tagging_gap']),
                    'high_cost_reviews': len([r for r in recommendations if r['type'] == 'high_cost_review'])
                },
                'total_estimated_monthly_savings': round(total_estimated_savings, 2),
                'total_estimated_annual_savings': round(total_estimated_savings * 12, 2),
                'avg_confidence': round(sum(r.get('confidence', 0) for r in recommendations) / max(len(recommendations), 1), 2),
                'top_opportunity': {
                    'type': recommendations[0]['type'] if recommendations else None,
                    'savings': recommendations[0].get('estimated_savings', 0) if recommendations else 0
                },
                'implementation_complexity': 'Low to Medium - mostly configuration and policy changes',
                'estimated_effort_hours': len(recommendations) * 2  # Rough estimate
            }
            
            logger.info(f"[{request_id}] Generated {len(recommendations)} recommendations with ${total_estimated_savings:,.2f} potential monthly savings")
            
            return RecommendationResponse(
                recommendations=recommendations,
                summary=summary,
                total_potential_savings=round(total_estimated_savings, 2),
                priority_breakdown=priority_counts,
                generated_at=datetime.utcnow().isoformat(),
                analysis_period=latest_month,
                request_id=request_id
            )
            
    except Exception as e:
        update_metrics('errors_total')
        logger.error(f"[{request_id}] Recommendations generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendations generation failed: {str(e)}")

@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get comprehensive system metrics and observability data for monitoring"""
    request_id = str(uuid4())
    
    try:
        logger.info(f"[{request_id}] Generating comprehensive system metrics")
        
        start_time = METRICS_STORE['start_time']
        uptime_hours = (datetime.utcnow() - start_time).total_seconds() / 3600
        
        total_requests = METRICS_STORE['api_requests_total']
        error_rate = (METRICS_STORE['errors_total'] / max(total_requests, 1)) * 100
        
        # Calculate comprehensive response time statistics
        response_times = METRICS_STORE['response_times']
        response_time_sum = METRICS_STORE['response_time_sum']
        avg_response_time = (response_time_sum / max(total_requests, 1)) * 1000  # Convert to milliseconds
        
        # Cache metrics
        total_cache_requests = METRICS_STORE['cache_hits'] + METRICS_STORE['cache_misses']
        cache_hit_rate = (METRICS_STORE['cache_hits'] / max(total_cache_requests, 1)) * 100
        
        # System health determination
        system_health = "healthy"
        if error_rate > 15:
            system_health = "critical"
        elif error_rate > 8:
            system_health = "warning"
        elif uptime_hours < 0.5:
            system_health = "starting"
        elif not rag_service:
            system_health = "degraded"
        
        # Performance statistics
        recent_times = [t * 1000 for t in response_times[-100:]]  # Last 100 in milliseconds
        performance_stats = {}
        
        if recent_times:
            recent_times_sorted = sorted(recent_times)
            performance_stats = {
                'min_response_time': round(min(recent_times), 2),
                'max_response_time': round(max(recent_times), 2),
                'median_response_time': round(recent_times_sorted[len(recent_times_sorted)//2], 2),
                'p95_response_time': round(recent_times_sorted[int(len(recent_times_sorted) * 0.95)], 2) if len(recent_times_sorted) > 20 else round(max(recent_times), 2),
                'p99_response_time': round(recent_times_sorted[int(len(recent_times_sorted) * 0.99)], 2) if len(recent_times_sorted) > 100 else round(max(recent_times), 2),
                'response_time_std_dev': round((sum((x - avg_response_time)**2 for x in recent_times) / len(recent_times))**0.5, 2) if len(recent_times) > 1 else 0.0
            }
        
        # Get recent response times for frontend display
        recent_response_times = [round(t * 1000, 2) for t in response_times[-50:]]
        
        # Clean up old hourly data (keep last 48 hours)
        current_requests_per_hour = dict(list(METRICS_STORE['requests_by_hour'].items())[-48:])
        
        # Token usage metrics
        token_usage = {
            'total_tokens_used': METRICS_STORE['gemini_tokens_used'],
            'input_tokens': METRICS_STORE['gemini_input_tokens'],
            'output_tokens': METRICS_STORE['gemini_output_tokens'],
            'estimated_cost': round(METRICS_STORE['gemini_tokens_used'])  # $0.005 per 1K tokens
        }
        
        logger.info(f"[{request_id}] System metrics generated: {system_health} health, {error_rate:.1f}% error rate")
        
        return MetricsResponse(
            uptime_hours=round(uptime_hours, 2),
            total_requests=total_requests,
            ai_queries=METRICS_STORE['ai_queries_total'],
            error_rate=round(error_rate, 2),
            avg_response_time=round(avg_response_time, 2),
            active_users=METRICS_STORE['active_users'],
            database_queries=METRICS_STORE['database_queries'],
            gemini_api_calls=METRICS_STORE['gemini_api_calls'],
            cache_hit_rate=round(cache_hit_rate, 2),
            security_blocks=METRICS_STORE['security_blocks'],
            validation_failures=METRICS_STORE['validation_failures'],
            requests_per_hour=current_requests_per_hour,
            recent_response_times=recent_response_times,
            system_health=system_health,
            error_breakdown=dict(METRICS_STORE['error_types']),
            performance_stats=performance_stats,
            token_usage=token_usage
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] Metrics generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics unavailable: {str(e)}")

@app.get("/api/analytics")
async def get_analytics():
    """Get usage analytics and insights for system optimization"""
    request_id = str(uuid4())
    
    try:
        logger.info(f"[{request_id}] Generating usage analytics")
        
        # Popular queries analysis
        popular_queries = []
        sorted_queries = sorted(METRICS_STORE['popular_queries'].items(), key=lambda x: x[1], reverse=True)
        
        for query, count in sorted_queries[:10]:
            popular_queries.append({
                'query': query[:50] + '...' if len(query) > 50 else query,
                'count': count,
                'percentage': round((count / max(METRICS_STORE['ai_queries_total'], 1)) * 100, 1)
            })
        
        # Error analysis
        error_analysis = dict(METRICS_STORE['error_types'])
        
        # Performance trends
        recent_times = METRICS_STORE['response_times'][-100:]
        performance_trend = "stable"
        if len(recent_times) > 20:
            first_half_avg = sum(recent_times[:len(recent_times)//2]) / (len(recent_times)//2)
            second_half_avg = sum(recent_times[len(recent_times)//2:]) / (len(recent_times) - len(recent_times)//2)
            
            if second_half_avg > first_half_avg * 1.2:
                performance_trend = "degrading"
            elif second_half_avg < first_half_avg * 0.8:
                performance_trend = "improving"
        
        # Usage patterns
        total_requests = METRICS_STORE['api_requests_total']
        uptime_hours = (datetime.utcnow() - METRICS_STORE['start_time']).total_seconds() / 3600
        requests_per_hour_avg = total_requests / max(uptime_hours, 1)
        
        analytics_data = {
            'summary': {
                'total_ai_queries': METRICS_STORE['ai_queries_total'],
                'total_requests': total_requests,
                'uptime_hours': round(uptime_hours, 1),
                'avg_requests_per_hour': round(requests_per_hour_avg, 1),
                'performance_trend': performance_trend,
                'primary_usage': 'cost_analysis' if METRICS_STORE['ai_queries_total'] > 0 else 'exploration'
            },
            'popular_queries': popular_queries,
            'error_analysis': error_analysis,
            'usage_patterns': {
                'peak_hour': max(METRICS_STORE['requests_by_hour'].items(), key=lambda x: x[1])[0] if METRICS_STORE['requests_by_hour'] else None,
                'avg_session_duration': 'not_implemented',  # Would need session tracking
                'user_retention': 'not_implemented',  # Would need user identification
                'feature_adoption': {
                    'ai_queries': round((METRICS_STORE['ai_queries_total'] / max(total_requests, 1)) * 100, 1),
                    'kpi_usage': 'estimated_high',
                    'recommendations_usage': 'estimated_medium'
                }
            },
            'system_insights': {
                'bottlenecks': ['database_queries', 'ai_processing'] if METRICS_STORE['ai_queries_total'] > 100 else ['none_detected'],
                'optimization_suggestions': [
                    'Implement query caching for repeated questions',
                    'Add database connection pooling for high load',
                    'Consider response compression for large datasets'
                ] if total_requests > 1000 else ['Monitor for growth patterns'],
                'capacity_planning': {
                    'current_load': 'low' if requests_per_hour_avg < 10 else 'medium' if requests_per_hour_avg < 50 else 'high',
                    'scaling_trigger': f"{requests_per_hour_avg * 5:.0f} requests/hour",
                    'estimated_capacity': f"{requests_per_hour_avg * 10:.0f} requests/hour with current setup"
                }
            },
            'generated_at': datetime.utcnow().isoformat(),
            'request_id': request_id
        }
        
        logger.info(f"[{request_id}] Analytics generated: {len(popular_queries)} popular queries, {len(error_analysis)} error types")
        
        return analytics_data
        
    except Exception as e:
        logger.error(f"[{request_id}] Analytics generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics unavailable: {str(e)}")

# Error handlers
@app.exception_handler(ValueError)
async def validation_exception_handler(request: Request, exc: ValueError):
    """Handle validation errors with detailed feedback"""
    update_metrics('validation_failures')
    logger.warning(f"Validation error: {str(exc)}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": str(exc),
            "type": "validation_error",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler"""
    logger.error(f"HTTP exception: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "type": "http_error",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    # Enhanced development server configuration
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        access_log=True,
        log_level="info"
    )