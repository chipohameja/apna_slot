from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

SUCCEEDED = "succeeded"
FAILED = "failed"
ABANDONED = "abandoned"
OUTCOMES = (SUCCEEDED, FAILED, ABANDONED)


@dataclass(frozen=True)
class CallbackResult:
	"""What the gateway says happened, after its signature has been checked."""

	outcome: str
	gateway_reference: str | None = None
	raw: dict = field(default_factory=dict)


class PaymentGateway(ABC):
	"""The seam a real gateway drops into (D-16). The transaction, the callback endpoint and
	the booking state machine are written against this interface, never against the mock."""

	name: str

	@abstractmethod
	def create_checkout(self, transaction) -> dict:
		"""Return `{"redirect_url", "gateway_reference"}` for a hosted payment page."""

	@abstractmethod
	def verify_callback(self, payload: dict) -> CallbackResult:
		"""Authenticate the callback. Raise on a bad signature; never trust a claimed outcome."""

	@abstractmethod
	def refund(self, transaction, amount: Decimal, reason: str) -> dict:
		"""Phase 6. Return `{"reference", "status"}`."""
