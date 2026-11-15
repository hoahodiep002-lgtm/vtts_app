"""Google Play Billing (STUB). Ban that: pyjnius -> BillingClient, xac thuc purchase."""
from core.config import PRO_PRODUCT_ID


class BillingManager:
    def __init__(self):
        self._is_pro = False

    @property
    def is_pro(self) -> bool:
        # TODO: queryPurchasesAsync, khong chi tin co luu local
        return self._is_pro

    def purchase_pro(self):
        raise NotImplementedError(f"Mua {PRO_PRODUCT_ID} qua Play Billing")
