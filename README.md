# Teledetection Drone Satellite Platform

A comprehensive platform for processing drone photos and teledetection using WebODM API and Google Earth Engine API. Built with modern microservices architecture and Docker for easy deployment and scalability.

## 🚀 Features

- **Microservices Architecture**: Modular design with independent services
- **Docker Containerization**: Easy deployment and replication
- **WebODM Integration**: Automated drone image processing
- **Google Earth Engine**: Satellite imagery analysis and processing
- **Modern Tech Stack**: FastAPI, React, PostgreSQL with PostGIS
- **Authentication & Authorization**: JWT-based security
- **Real-time Processing**: Celery-based task queue
- **Interactive Visualization**: Web-based map interface

## 🏗️ Architecture

### Services

1. **API Gateway** (Port 8000) - Request routing and load balancing
2. **Authentication Service** (Port 8001) - User management and JWT tokens
3. **File Service** (Port 8002) - File upload, storage, and metadata management
4. **WebODM Service** (Port 8003) - Integration with WebODM for drone image processing
5. **Google Earth Engine Service** (Port 8004) - Satellite imagery and analysis
6. **Processing Service** (Port 8005) - Task orchestration and workflow management
7. **Analysis Service** (Port 8006) - Image analysis and algorithms
8. **Visualization Service** (Port 8007) - Map layers and visualization
9. **Frontend Application** (Port 3000) - React-based web interface

### Infrastructure

- **PostgreSQL + PostGIS**: Spatial database for metadata and results
- **Redis**: Caching and message broker for Celery
- **Nginx**: Reverse proxy and load balancer
- **Docker Compose**: Container orchestration

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM
- **Celery**: Distributed task queue
- **Redis**: In-memory data store
- **PostgreSQL + PostGIS**: Spatial database

### Frontend
- **React + Next.js**: Modern web framework
- **Leaflet/OpenLayers**: Interactive maps
- **Material-UI/Tailwind**: UI components

### External APIs
- **WebODM API**: Drone image processing
- **Google Earth Engine API**: Satellite imagery
- **Cloud Storage**: AWS S3/Google Cloud Storage

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd teledetection_drone_satellite
   ```

2. **Copy environment variables**
   ```bash
   cp .env.example .env
   ```

3. **Edit environment variables**
   ```bash
   nano .env
   ```
   
   Update the following variables:
   - `POSTGRES_PASSWORD`: Set a secure password
   - `JWT_SECRET`: Set a secure JWT secret key
   - `WEBODM_API_URL`: Your WebODM instance URL
   - `WEBODM_API_TOKEN`: Your WebODM API token
   - `GEE_PROJECT_ID`: Your Google Earth Engine project ID

4. **Create credentials directory for Google Earth Engine**
   ```bash
   mkdir -p credentials
   # Copy your GEE service account JSON file to credentials/gee-service-account.json
   ```

5. **Start the services**
   ```bash
   docker-compose up -d
   ```

6. **Check service health**
   ```bash
   curl http://localhost:8000/health
   ```

### Development Setup

For development with hot reloading:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## 📁 Project Structure

```
teledetection_drone_satellite/
├── docker-compose.yml              # Main Docker Compose configuration
├── .env.example                    # Environment variables template
├── services/                       # Microservices
│   ├── api-gateway/               # API Gateway service
│   ├── auth-service/              # Authentication service
│   ├── file-service/              # File management service
│   ├── webodm-service/            # WebODM integration service
│   ├── gee-service/               # Google Earth Engine service
│   ├── processing-service/        # Processing pipeline service
│   ├── analysis-service/          # Analysis service
│   └── visualization-service/     # Visualization service
├── frontend/                      # React frontend application
├── database/                      # Database schemas and migrations
│   ├── migrations/               # Database migration files
│   └── schemas/                  # Database schema definitions
├── shared/                       # Shared code between services
│   ├── models/                   # Pydantic models
│   ├── utils/                    # Utility functions
│   └── config/                   # Configuration settings
├── scripts/                      # Utility scripts
├── docs/                         # Documentation
└── tests/                        # Test files
```

## 🔧 Configuration

### Environment Variables

Key environment variables to configure:

- **Database**: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- **Security**: `JWT_SECRET`, `JWT_EXPIRE_MINUTES`
- **WebODM**: `WEBODM_API_URL`, `WEBODM_API_TOKEN`
- **Google Earth Engine**: `GOOGLE_APPLICATION_CREDENTIALS`, `GEE_PROJECT_ID`
- **Storage**: `STORAGE_PATH`, `MAX_FILE_SIZE`

### Service Configuration

Each service can be configured independently through environment variables. See individual service documentation for specific configuration options.

## 📊 Current Implementation Status

### ✅ Completed
- [x] Project structure and Docker configuration
- [x] Shared models and utilities
- [x] Database schema with PostGIS support
- [x] API Gateway with request routing
- [x] Authentication service with JWT tokens
- [x] Basic middleware (logging, metrics, CORS)

### 🚧 In Progress
- [ ] File management service
- [ ] WebODM integration service
- [ ] Google Earth Engine service
- [ ] Processing pipeline service

### 📋 Planned
- [ ] Analysis service
- [ ] Visualization service
- [ ] Frontend application
- [ ] Testing suite
- [ ] Documentation
- [ ] Deployment scripts

## 🔌 API Endpoints

### Authentication Service
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/verify` - Verify token
- `GET /api/v1/auth/me` - Get current user

### File Service (Planned)
- `POST /api/v1/files/upload` - Upload files
- `GET /api/v1/files/{file_id}` - Get file info
- `DELETE /api/v1/files/{file_id}` - Delete file

### Processing Service (Planned)
- `POST /api/v1/processing/tasks` - Create processing task
- `GET /api/v1/processing/tasks/{task_id}` - Get task status
- `GET /api/v1/processing/tasks` - List tasks

## 🧪 Testing

Run tests with:
```bash
docker-compose exec api-gateway pytest
```

## 📚 Documentation

- API documentation available at: `http://localhost:8000/docs`
- Individual service docs at: `http://localhost:800X/docs` (where X is service port)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation in the `docs/` directory
- Review service logs: `docker-compose logs <service-name>`

## 🔄 Development Roadmap

### Phase 1: Foundation ✅
- [x] Project structure
- [x] Docker configuration
- [x] Database schema
- [x] API Gateway
- [x] Authentication service

### Phase 2: Core Services (Current)
- [ ] File management service
- [ ] WebODM integration
- [ ] Google Earth Engine integration
- [ ] Processing pipeline

### Phase 3: Analysis & Visualization
- [ ] Analysis algorithms
- [ ] Visualization service
- [ ] Frontend application

### Phase 4: Production Ready
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Monitoring and logging
- [ ] Deployment automation