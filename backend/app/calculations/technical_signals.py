def calculate_dma_signal(cmp: float, dma_50: float, dma_200: float) -> str:
    """
    Unified logic for DMA technical signals.
    Returns: "bullish", "bearish", "long term bullish, near term bearish", 
             "near term bullish, long term bearish", "neutral"
    """
    if not dma_50 or not dma_200 or not cmp:
        return "neutral"
        
    if cmp >= dma_50 and cmp >= dma_200:
        return "bullish"
    elif cmp < dma_50 and cmp < dma_200:
        return "bearish"
    elif cmp < dma_50 and cmp >= dma_200:
        return "long term bullish, near term bearish"
    elif cmp >= dma_50 and cmp < dma_200:
        return "near term bullish, long term bearish"
    
    return "neutral"
