export const formatPrice = (price: number, decimals = 5): string => {
  return price.toFixed(decimals);
};
