from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .services import DashboardService


@extend_schema(tags=['Dashboard'], summary="Get overview KPIs with server-computed deltas")
class DashboardOverviewView(APIView):
    def get(self, request):
        kpis = DashboardService.get_overview_kpis()
        return Response(kpis, status=status.HTTP_200_OK)


@extend_schema(tags=['Dashboard'], summary="Get Requires Attention alert items with severity ranking")
class DashboardAttentionView(APIView):
    def get(self, request):
        attention = DashboardService.get_attention_items()
        return Response(attention, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Analytics'],
    summary="Get bookings timeline aggregation",
    parameters=[
        OpenApiParameter(name='range', description='Time range: 24h, 7d, 30d', required=False, type=str, default='7d')
    ]
)
class AnalyticsBookingsView(APIView):
    def get(self, request):
        range_param = request.query_params.get('range', '7d')
        # Validate at the view level — don't silently default invalid values.
        # Returns 400 for unrecognized range values like ?range=garbage.
        VALID_BOOKING_RANGES = ['24h', '7d', '30d']
        if range_param not in VALID_BOOKING_RANGES:
            return Response(
                {
                    "error": {
                        "code": "INVALID_RANGE",
                        "message": f"Invalid range '{range_param}'. Must be one of: {', '.join(VALID_BOOKING_RANGES)}",
                        "details": {"valid_ranges": VALID_BOOKING_RANGES, "received": range_param}
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        data = DashboardService.get_analytics_bookings(range_param=range_param)
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Analytics'],
    summary="Get revenue timeline aggregation",
    parameters=[
        OpenApiParameter(name='range', description='Time range: 7d, 30d', required=False, type=str, default='7d')
    ]
)
class AnalyticsRevenueView(APIView):
    def get(self, request):
        range_param = request.query_params.get('range', '7d')
        VALID_REVENUE_RANGES = ['7d', '30d']
        if range_param not in VALID_REVENUE_RANGES:
            return Response(
                {
                    "error": {
                        "code": "INVALID_RANGE",
                        "message": f"Invalid range '{range_param}'. Must be one of: {', '.join(VALID_REVENUE_RANGES)}",
                        "details": {"valid_ranges": VALID_REVENUE_RANGES, "received": range_param}
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        data = DashboardService.get_analytics_revenue(range_param=range_param)
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(tags=['Analytics'], summary="Get status distribution donut data")
class AnalyticsStatusView(APIView):
    def get(self, request):
        data = DashboardService.get_analytics_status()
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(tags=['Analytics'], summary="Get service category breakdown")
class AnalyticsServicesView(APIView):
    def get(self, request):
        data = DashboardService.get_analytics_services()
        return Response(data, status=status.HTTP_200_OK)
