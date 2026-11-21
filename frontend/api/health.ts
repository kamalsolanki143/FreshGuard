import { handleProxy, VercelRequest, VercelResponse } from "./_lib/proxy";

export default async function healthHandler(req: VercelRequest, res: VercelResponse) {
  return handleProxy(req, res, "/health");
}
