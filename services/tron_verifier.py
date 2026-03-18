import aiohttp
import logging
from aiogram import Bot
from config import USDT_TRC20_WALLET, MIN_DEPOSIT, TRONSCAN_API

logger = logging.getLogger(__name__)

async def verify_trc20(txid: str, expected_amount: float, bot: Bot = None):
    """
    Verify a TRC20 USDT transaction via TronScan API.
    """
    url = f"{TRONSCAN_API}"
    params = {"hash": txid.strip()}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    if bot:
                        from services.group_notifications import notify_system_log
                        await notify_system_log(bot, "API Error", f"TronScan returned status {resp.status}")
                    return False, "Error al conectar con TronScan."
                data = await resp.json()
    except Exception as e:
        logger.error(f"TronScan request error: {e}")
        return False, "No se pudo conectar con la red TRON."
    
    if not data or "contractRet" not in data:
        return False, "Transacción no encontrada."

    if data.get("contractRet") != "SUCCESS":
        return False, "La transacción no fue exitosa."

    if not data.get("confirmed") and data.get("confirmations", 0) < 1:
        return False, "La transacción aún no tiene confirmaciones suficientes (mínimo 1)."

    # Extract token transfer info
    token_info_list = data.get("trc20TransferInfo", [])
    
    if not token_info_list:
        # Fallback to tokenTransferInfo if trc20TransferInfo is missing
        backup_info = data.get("tokenTransferInfo")
        if backup_info:
            token_info_list = [backup_info]
        else:
            return False, "No se encontró transferencia de tokens TRC20."

    found_usdt = False
    for token_info in token_info_list:
        symbol = token_info.get("symbol") or token_info.get("tokenAbbr")
        if symbol == "USDT":
            to_address = token_info.get("to_address")
            
            # Strict wallet validation
            if to_address != USDT_TRC20_WALLET:
                logger.warning(f"Invalid wallet detected: {to_address}")
                return False, f"La billetera de destino no es la correcta."

            print(f"Deposit detected to {to_address}")
            logger.info(f"Deposit detected to {to_address}")
            
            try:
                raw_amount = int(token_info.get("amount_str") or token_info.get("amount", 0))
                decimals = int(token_info.get("decimals", 6))
                amount = raw_amount / (10 ** decimals)
            except:
                continue
            
            if amount >= expected_amount:
                found_usdt = True
                break
            else:
                return False, f"Monto insuficiente. Recibido: {amount} USDT."

    if not found_usdt:
        return False, "La transacción no es un depósito de USDT válido."
    
    return True, "Transacción verificada."
