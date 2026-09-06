APP_NAME = "FinAssist AI"
MODEL_NAME = "MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33"
CONFIDENCE_THRESHOLD = 0.40
MAX_INPUT_LENGTH = 500

INTENTS = [
    "card payment issue",
    "cash withdrawal issue",
    "money transfer issue",
    "account access issue",
    "refund issue",
    "cash deposit issue",
    "fees and charges question",
    "identity verification issue",
    "general account question",
]

RESPONSES = {
    "card payment issue": (
        "I can help with a card payment issue. Check whether the payment is pending, "
        "declined, duplicated, or unfamiliar. Never share your PIN, CVV, password, or OTP. "
        "If you do not recognize the transaction, freeze the card in the official app and contact support."
    ),
    "cash withdrawal issue": (
        "I can help with an ATM or cash withdrawal issue. Check the transaction status in your activity. "
        "If your balance was charged but cash was not received, keep the ATM receipt or reference number "
        "and report the transaction through official support."
    ),
    "money transfer issue": (
        "I can help with a transfer issue. Verify the recipient details and transaction status. "
        "If the transfer is pending, avoid sending the same payment again until the first transaction is resolved."
    ),
    "account access issue": (
        "I can help with account access. Use the official password-reset or account-recovery option in the app. "
        "Never share your password, OTP, PIN, or recovery code with anyone."
    ),
    "refund issue": (
        "I can help with a refund issue. Check the original transaction and refund status in your activity. "
        "Refund timing can depend on the merchant and payment network, so use official support if it remains unresolved."
    ),
    "cash deposit issue": (
        "I can help with a deposit issue. Check whether the deposit appears as pending or completed. "
        "Keep any receipt or reference number and contact official support if the balance does not update."
    ),
    "fees and charges question": (
        "I can help explain a fee or charge. Identify the fee shown in your transaction history. "
        "For the exact current amount, refer to the fintech app's official fee schedule."
    ),
    "identity verification issue": (
        "I can help with identity verification. Follow the secure in-app verification instructions and make sure "
        "the information entered matches your official records. Only upload documents through the official secure flow."
    ),
    "general account question": (
        "I can help with general account questions. Please describe what you want to do, such as checking a transaction, "
        "managing your card, making a transfer, or updating account settings."
    ),
}
