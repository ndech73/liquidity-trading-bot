export const formatPercentage = (value: number, decimals = 2): string => {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(decimals)}%`;
};
