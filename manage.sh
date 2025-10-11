#!/bin/bash

# Ecommerce Microservices Management Script
# Usage: ./manage.sh [start|stop|restart|status|logs|build|obs-start|obs-stop]

set -e

MICROSERVICES_COMPOSE="docker-compose.microservices.yml"
OBSERVABILITY_COMPOSE="docker-compose.observability.yml"
PROJECT_NAME="ecommerce-microservices"

case "${1:-help}" in
    start)
        echo "🚀 Starting all microservices..."
        docker compose -f $MICROSERVICES_COMPOSE up -d
        echo "✅ All microservices started!"
        echo ""
        echo "📊 Service URLs:"
        echo "  • 🚀 Nginx Load Balancer: http://localhost:8000"
        echo "  • 📊 Load Balancer Status: http://localhost:8000/status"
        echo "  • 👥 User Service 1: http://localhost:8011 (direct)"
        echo "  • 👥 User Service 2: http://localhost:8012 (direct)"
        echo "  • 👥 User Service 3: http://localhost:8013 (direct)"
        echo "  • 🛒 Product Service: http://localhost:8002 (when enabled)"
        echo "  • 📋 Order Service: http://localhost:8003 (when enabled)"
        echo "  • 📬 Notification Service: http://localhost:8004 (when enabled)"
        echo "  • 🎛️  Kafka UI: http://localhost:8080"
        echo "  • 🗄️  PostgreSQL: localhost:5432"
        echo "  • 🔴 Redis: localhost:6380"
        ;;
    
    stop)
        echo "🛑 Stopping all microservices..."
        docker compose -f $MICROSERVICES_COMPOSE down
        echo "✅ All microservices stopped!"
        ;;
    
    restart)
        echo "🔄 Restarting all microservices..."
        docker compose -f $MICROSERVICES_COMPOSE down
        docker compose -f $MICROSERVICES_COMPOSE up -d
        echo "✅ All microservices restarted!"
        ;;
    
    obs-start)
        echo "📊 Starting observability stack..."
        docker compose -f $OBSERVABILITY_COMPOSE up -d
        echo "✅ Observability stack started!"
        echo ""
        echo "📊 Observability URLs:"
        echo "  • 📈 Kibana (Logs): http://localhost:5601"
        echo "  • 🔍 Jaeger (Tracing): http://localhost:16686" 
        echo "  • 📊 Grafana (Metrics): http://localhost:3000 (admin/admin123)"
        echo "  • 🎯 Prometheus: http://localhost:9090"
        echo "  • 🔍 Elasticsearch: http://localhost:9200"
        ;;
    
    obs-stop)
        echo "🛑 Stopping observability stack..."
        docker compose -f $OBSERVABILITY_COMPOSE down
        echo "✅ Observability stack stopped!"
        ;;
    
    start-all)
        echo "🚀 Starting complete system (microservices + observability)..."
        docker compose -f $MICROSERVICES_COMPOSE up -d
        docker compose -f $OBSERVABILITY_COMPOSE up -d
        echo "✅ Complete system started!"
        echo ""
        echo "🏪 Microservice URLs:"
        echo "  • 🚀 Nginx Load Balancer: http://localhost:8000"
        echo "  • 👥 User Service: http://localhost:8011-8013"
        echo "  • 🛒 Product/Order/Notification: http://localhost:8002-8004"
        echo ""
        echo "📊 Observability URLs:"
        echo "  • 📈 Kibana (Logs): http://localhost:5601"
        echo "  • 🔍 Jaeger (Tracing): http://localhost:16686"
        echo "  • 📊 Grafana (Metrics): http://localhost:3000"
        ;;
    
    stop-all)
        echo "🛑 Stopping complete system..."
        docker compose -f $MICROSERVICES_COMPOSE down
        docker compose -f $OBSERVABILITY_COMPOSE down
        echo "✅ Complete system stopped!"
        ;;
    
    status)
        echo "📋 Microservices Status:"
        docker compose -f $MICROSERVICES_COMPOSE ps
        echo ""
        echo "📊 Observability Status:"
        docker compose -f $OBSERVABILITY_COMPOSE ps
        ;;
    
    logs)
        if [ -z "$2" ]; then
            echo "📜 Showing microservices logs (last 50 lines):"
            docker compose -f $MICROSERVICES_COMPOSE logs --tail=50
        else
            echo "📜 Showing logs for $2:"
            docker compose -f $MICROSERVICES_COMPOSE logs --tail=100 -f "$2"
        fi
        ;;
    
    obs-logs)
        if [ -z "$2" ]; then
            echo "📜 Showing observability logs (last 50 lines):"
            docker compose -f $OBSERVABILITY_COMPOSE logs --tail=50
        else
            echo "📜 Showing observability logs for $2:"
            docker compose -f $OBSERVABILITY_COMPOSE logs --tail=100 -f "$2"
        fi
        ;;
    
    build)
        echo "🔨 Building all microservices..."
        docker compose -f $MICROSERVICES_COMPOSE build
        echo "✅ All microservices built!"
        ;;
    
    clean)
        echo "🧹 Cleaning up containers, networks, and volumes..."
        docker compose -f $MICROSERVICES_COMPOSE down -v --remove-orphans
        docker compose -f $OBSERVABILITY_COMPOSE down -v --remove-orphans
        docker system prune -f
        echo "✅ Cleanup complete!"
        ;;
    
    test-lb)
        echo "🧪 Testing Nginx Load Balancer..."
        if [ -f "./test_nginx_lb.sh" ]; then
            ./test_nginx_lb.sh
        else
            echo "Testing basic Nginx health:"
            curl -s http://localhost:8000/nginx-health || echo "❌ Nginx Load Balancer not responding"
            echo ""
            echo "Testing Load Balancer routing (5 requests):"
            for i in {1..5}; do
                echo -n "Request $i: "
                response=$(curl -s http://localhost:8000/health 2>/dev/null)
                if [[ $response == *"service_name"* ]]; then
                    service_name=$(echo $response | grep -o '"service_name":"[^"]*"' | cut -d'"' -f4)
                    echo "✅ Routed to $service_name"
                else
                    echo "❌ Failed or no service info"
                fi
            done
        fi
        ;;
    
    help|*)
        echo "🛠️  Ecommerce Microservices Management"
        echo ""
        echo "Usage: ./manage.sh [command]"
        echo ""
        echo "🏪 Microservices Commands:"
        echo "  start         Start microservices only"
        echo "  stop          Stop microservices only"
        echo "  restart       Restart microservices"
        echo "  logs          Show microservices logs"
        echo "  build         Build microservice images"
        echo ""
        echo "📊 Observability Commands:"
        echo "  obs-start     Start observability stack only"
        echo "  obs-stop      Stop observability stack only"
        echo "  obs-logs      Show observability logs"
        echo ""
        echo "🚀 Complete System Commands:"
        echo "  start-all     Start everything (microservices + observability)"
        echo "  stop-all      Stop everything"
        echo "  status        Show status of all services"
        echo "  clean         Stop everything and clean up resources"
        echo ""
        echo "🧪 Testing Commands:"
        echo "  test-lb       Test load balancer functionality"
        echo ""
        echo "Examples:"
        echo "  ./manage.sh start-all          # Start complete system"
        echo "  ./manage.sh start              # Start only microservices"
        echo "  ./manage.sh obs-start          # Start only observability"
        echo "  ./manage.sh logs api-gateway   # Show specific service logs"
        echo "  ./manage.sh obs-logs kibana    # Show observability logs"
        ;;
esac