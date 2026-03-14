import aiohttp
import logging
from config import TRC20_WALLET, MIN_DEPOSIT, TRONSCAN_API

logger = logging.getLogger(__name__)

USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

async def verify_trc20(txid: str):
    """
    Verify a TRC20 USDT transaction via TronScan API.
    
    Returns:
        (True, amount_float)  — if valid
        (False, error_string) — if invalid
    """
    url = f"{TRONSCAN_API}?hash={txid.strip()}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return False, "Error al conectar con TronScan."
                data = await resp.json()
    except Exception as e:
        logger.error(f"TronScan request error: {e}")
        return False, "No se pudo conectar con la red TRON."
    
    # Extract token transfer info
    token_info = data.get("tokenTransferInfo")
    
    if not token_info:
        return False, "Transacción no válida o no es una transferencia de tokens."

    # Check it's USDT
    if token_info.get("tokenAbbr") != "USDT":
        return False, "El token recibido no es USDT TRC20."

    # Check receiver address
    if token_info.get("to_address") != TRC20_WALLET:
        return False, "La dirección de destino no coincide con nuestra wallet."
    
    # Must be successful
    if data.get("contractRet") != "SUCCESS":
        return False, f"La transacción no fue exitosa: {data.get('contractRet')}"

    # Extract amount
    try:
        raw_amount = int(token_info.get("amount_str", "0"))
        amount = raw_amount / 1_000_000
    except:
        return False, "Error al procesar el monto de la transacción."
    
    if amount < MIN_DEPOSIT:
        return False, f"El monto (${amount}) es menor al mínimo requerido (${MIN_DEPOSIT})."
    
    logger.info(f"TRC20 TX verified: {txid} — {amount} USDT")
    return True, round(amount, 2)
