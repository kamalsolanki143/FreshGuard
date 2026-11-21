import { handleProxy, VercelRequest, VercelResponse } from "../_lib/proxy";

export default async function readyHandler(req: VercelRequest, res: VercelResponse) {
  return handleProxy(req, res, "/health/ready");
}
