
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Publisher, User
from .permissions import IsReader


class SubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsReader]

    def get(self, request):
        user = request.user

        return Response({
            "publishers": list(
                user.subscribed_publishers.values("id", "name")
            ),
            "journalists": list(
                user.subscribed_journalists.values("id", "username")
            ),
        })

    def post(self, request):
        user = request.user
        subscription_type = request.data.get("type")
        item_id = request.data.get("id")
        action = request.data.get("action", "subscribe")

        if subscription_type not in ("publisher", "journalist"):
            return Response(
                {"detail": "Type must be publisher or journalist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action not in ("subscribe", "unsubscribe"):
            return Response(
                {"detail": "Action must be subscribe or unsubscribe."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not item_id:
            return Response(
                {"detail": "An id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            item_id = int(item_id)
        except (ValueError, TypeError):
            return Response(
                {"detail": "The id must be a number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subscription_type == "publisher":
            try:
                target = Publisher.objects.get(pk=item_id)
            except Publisher.DoesNotExist:
                return Response(
                    {"detail": "Publisher not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            relation = user.subscribed_publishers

        else:
            try:
                target = User.objects.get(
                    pk=item_id,
                    role=User.Role.JOURNALIST,
                )
            except User.DoesNotExist:
                return Response(
                    {"detail": "Journalist not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            relation = user.subscribed_journalists

        if action == "subscribe":
            relation.add(target)
            message = f"Subscribed to {subscription_type}."
        else:
            relation.remove(target)
            message = f"Unsubscribed from {subscription_type}."

        return Response(
            {"detail": message},
            status=status.HTTP_200_OK,
        )
