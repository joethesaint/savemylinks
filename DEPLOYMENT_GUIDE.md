# SaveMyLinks Deployment Guide

## Application Entry Points

SaveMyLinks provides two different application entry points, each designed for specific use cases and environments.

### 🚀 main.py - Development & Simple Deployments

**Purpose**: Lightweight FastAPI application for development and simple production deployments.

**Features**:
- Basic FastAPI setup with CORS
- Simple environment-based CORS configuration
- Static file serving
- Template rendering
- Health check endpoint
- Database initialization
- Minimal middleware stack

**When to Use**:
- ✅ Local development
- ✅ Simple production deployments
- ✅ Containerized environments with external security layers
- ✅ When you don't need advanced security features
- ✅ Quick prototyping and testing

**Run Command**:
```bash
python -m app.main
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 🛡️ main_enhanced.py - Production & Enterprise Deployments

**Purpose**: Full-featured FastAPI application with enterprise-grade security, monitoring, and performance features.

**Enhanced Features**:
- 🔒 **Security Middleware**: Rate limiting, security headers, trusted hosts
- 📊 **Structured Logging**: Request logging, performance monitoring, security events
- ⚡ **Caching System**: Redis-compatible caching with TTL management
- 🛠️ **Configuration Management**: Pydantic settings with environment validation
- 🚨 **Exception Handling**: Comprehensive error handling and reporting
- 📈 **Health Monitoring**: Advanced health checks and metrics
- 🔧 **Debug Endpoints**: Configuration and error testing (disabled in production)
- 🧹 **Background Tasks**: Cache maintenance and cleanup

**When to Use**:
- ✅ **Production environments**
- ✅ **Enterprise deployments**
- ✅ **High-traffic applications**
- ✅ **Security-sensitive environments**
- ✅ **Applications requiring monitoring and observability**
- ✅ **Multi-environment deployments (dev/staging/prod)**

**Run Command**:
```bash
python -m app.main_enhanced
# or
uvicorn app.main_enhanced:app --host 0.0.0.0 --port 8000
```

## Environment Configuration

### main_enhanced.py Environment Variables

The enhanced application requires proper environment configuration:

```bash
# Required
ENVIRONMENT=production  # development, staging, production
DATABASE_URL=postgresql://user:pass@localhost/db

# Security (Recommended for Production)
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Caching (Optional)
CACHE_ENABLED=true
CACHE_TTL=300
CACHE_MAX_SIZE=1000

# Logging (Optional)
LOG_LEVEL=INFO
LOG_FILE=logs/savemylinks.log
```

### main.py Environment Variables

The basic application only requires:

```bash
# Optional
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
DATABASE_URL=sqlite:///./savemylinks.db
```

## Production Deployment Recommendations

### For Production Use main_enhanced.py

**Why?**
- Security headers protect against common web vulnerabilities
- Rate limiting prevents abuse and DoS attacks
- Request logging provides audit trails
- Structured configuration management
- Performance monitoring and caching
- Proper error handling and reporting

### Security Considerations

1. **Disable Debug Features**: main_enhanced.py automatically disables debug endpoints and API docs in production
2. **Environment Validation**: Settings are validated at startup
3. **Security Headers**: Automatic CSP, HSTS, and other security headers
4. **Rate Limiting**: Configurable per-IP rate limiting
5. **Trusted Hosts**: Host header validation

## Docker Deployment

### Development (main.py)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "-m", "app.main"]
```

### Production (main_enhanced.py)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
ENV ENVIRONMENT=production
CMD ["python", "-m", "app.main_enhanced"]
```

## Migration Path

### From main.py to main_enhanced.py

1. **Update Environment Variables**: Add required configuration
2. **Test in Staging**: Verify all features work with your setup
3. **Update Deployment Scripts**: Change entry point
4. **Monitor**: Use the enhanced logging and monitoring features

### Gradual Migration

You can run both versions side by side during migration:
- Keep main.py for development
- Deploy main_enhanced.py to staging/production
- Gradually migrate all environments

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**: main_enhanced.py will fail to start with clear error messages
2. **Cache Connection**: Disable caching if Redis is not available (`CACHE_ENABLED=false`)
3. **Rate Limiting**: Adjust limits based on your traffic patterns
4. **CORS Issues**: Ensure ALLOWED_ORIGINS is properly configured

### Debug Mode

For production debugging, temporarily set:
```bash
ENVIRONMENT=development
```
This will re-enable debug endpoints and API documentation.

## Performance Comparison

| Feature | main.py | main_enhanced.py |
|---------|---------|------------------|
| Startup Time | ~1s | ~2-3s |
| Memory Usage | ~50MB | ~80-120MB |
| Request Latency | Low | Low + middleware overhead |
| Security | Basic | Enterprise-grade |
| Monitoring | None | Comprehensive |
| Caching | None | Redis-compatible |

## Conclusion

- **Use main.py** for development, testing, and simple deployments
- **Use main_enhanced.py** for production, enterprise, and security-sensitive environments
- Both applications are fully compatible and can be swapped without data loss
- The enhanced version provides significant security and operational benefits for production use