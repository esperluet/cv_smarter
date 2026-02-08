export function normalizeError(error) {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error";
}
