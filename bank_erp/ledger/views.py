from django.db import transaction
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.response import Response

from .models import Customer, Invoice, Payment


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "customer_id", "name")


class InvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    amount_paid = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "customer",
            "customer_name",
            "amount",
            "amount_paid",
            "balance",
            "due_date",
            "status",
        )


class PaymentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(write_only=True)
    invoice = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "invoice",
            "invoice_number",
            "amount",
            "reference",
            "idempotency_key",
            "booked_at",
        )
        read_only_fields = ("id", "invoice", "booked_at")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate(self, attrs):
        invoice_number = attrs.pop("invoice_number")
        try:
            attrs["_invoice"] = Invoice.objects.get(invoice_number=invoice_number)
        except Invoice.DoesNotExist:
            raise serializers.ValidationError({"invoice_number": "Invoice not found."})
        return attrs

    def create(self, validated_data):
        return Payment.objects.create(
            invoice=validated_data["_invoice"],
            amount=validated_data["amount"],
            reference=validated_data.get("reference", ""),
            idempotency_key=validated_data["idempotency_key"],
        )


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.all().order_by("customer_id")
    serializer_class = CustomerSerializer


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Invoice.objects.select_related("customer").prefetch_related("payments").all()
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        invoice_status = self.request.query_params.get("status")
        if invoice_status == "unpaid":
            queryset = queryset.filter(status__in=["open", "partially_paid"])
        elif invoice_status:
            queryset = queryset.filter(status=invoice_status)
        return queryset.order_by("invoice_number")


class PaymentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Payment.objects.select_related("invoice").all().order_by("-booked_at")
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        request_key = request.data.get("idempotency_key")
        if request_key:
            existing = Payment.objects.select_related("invoice").filter(
                idempotency_key=request_key
            ).first()
            if existing:
                return Response(
                    PaymentSerializer(existing, context=self.get_serializer_context()).data,
                    status=status.HTTP_200_OK,
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        idempotency_key = serializer.validated_data["idempotency_key"]
        existing = Payment.objects.select_related("invoice").filter(
            idempotency_key=idempotency_key
        ).first()
        if existing:
            return Response(
                PaymentSerializer(existing, context=self.get_serializer_context()).data,
                status=status.HTTP_200_OK,
            )

        invoice = serializer.validated_data["_invoice"]
        amount = serializer.validated_data["amount"]

        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().select_related("customer").get(
                pk=invoice.pk
            )
            if invoice.status == Invoice.Status.PAID:
                return Response(
                    {"detail": "Invoice is already paid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if amount > invoice.balance:
                return Response(
                    {"detail": "Payment amount exceeds the invoice balance."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment = Payment.objects.create(
                invoice=invoice,
                amount=amount,
                reference=serializer.validated_data.get("reference", ""),
                idempotency_key=idempotency_key,
            )

            paid = invoice.amount_paid
            if paid >= invoice.amount:
                invoice.status = Invoice.Status.PAID
            elif paid > 0:
                invoice.status = Invoice.Status.PARTIALLY_PAID
            else:
                invoice.status = Invoice.Status.OPEN
            invoice.save(update_fields=["status"])

        result = PaymentSerializer(
            payment,
            context=self.get_serializer_context(),
        )
        headers = self.get_success_headers(result.data)
        return Response(result.data, status=status.HTTP_201_CREATED, headers=headers)
