export async function requestWithRefresh({ execute, hasRefreshToken, refreshSession, retry = true }) {
  try {
    return await execute();
  } catch (error) {
    if (error?.status === 401 && retry && hasRefreshToken()) {
      const refreshed = await refreshSession();
      if (refreshed) {
        return requestWithRefresh({
          execute,
          hasRefreshToken,
          refreshSession,
          retry: false,
        });
      }
    }
    throw error;
  }
}
