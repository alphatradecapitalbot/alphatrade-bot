import requests
import logging
from config import TRONSCAN_API, USDT_TRC20_WALLET

logger = logging.getLogger(__name__)

def verify_transaction(txid: str, expected_amount: float, expected_address: str = USDT_TRC20_WALLET):
    """
    Verifies a TRC20 (USDT) transaction using Tronscan API.
    
    Checks:
    - TXID exists
    - Token is USDT
    - Destination address matches
    - Amount is >= expected_amount
    - Transaction has confirmations (confirmed status)
    """
    try:
        params = {"hash": txid}
        response = requests.get(TRONSCAN_API, params=params, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Tronscan API error: {response.status_code}")
            return False, "Error al conectar con la API de TRONSCAN."

        data = response.json()
        
        # Check if transaction exists
        if not data or "contractRet" not in data:
            return False, "Transacción no encontrada."

        # Check status
        if data.get("contractRet") != "SUCCESS":
            return False, "La transacción no fue exitosa."

        # Check confirmations (confirmed status in Tronscan)
        if not data.get("confirmed"):
            return False, "La transacción aún no tiene confirmaciones suficientes."

        # Find USDT (TRC20) transfer info
        # Tronscan API response varies, usually it's in 'trc20TransferInfo' or we check the 'trigger_info'
        trc20_transfers = data.get("trc20TransferInfo", [])
        
        if not trc20_transfers:
            return False, "No se encontró transferencia de tokens TRC20."

        found_usdt = False
        for transfer in trc20_transfers:
            # USDT Contract Address in Tron Mainnet
            # TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
            symbol = transfer.get("symbol", "").upper()
            to_address = transfer.get("to_address")
            amount_str = transfer.get("amount_str") or str(transfer.get("amount", 0))
            decimals = int(transfer.get("decimals", 6))
            
            # Use raw amount if amount_str is missing, handle decimals
            try:
                actual_amount = float(amount_str) / (10 ** decimals)
            except:
                actual_amount = 0
            
            # Log for debugging
            logger.info(f"Checking transfer: {symbol}, To: {to_address}, Amount: {actual_amount}")

            if symbol == "USDT" and to_address == expected_address:
                if actual_amount >= expected_amount:
                    found_usdt = True
                    break
                else:
                    return False, f"Monto insuficiente. Se recibió {actual_amount} USDT, se esperaba {expected_amount} USDT."

        if not found_usdt:
            return False, "La transacción no es un depósito de USDT a la billetera correcta."

        return True, "Transacción verificada."

    except Exception as e:
        logger.error(f"Error verifying transaction {txid}: {e}")
        return False, f"Error durante la verificación: {str(e)}"
