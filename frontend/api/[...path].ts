import { handleProxy, VercelRequest, VercelResponse } from "./_lib/proxy";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  return handleProxy(req, res);
}
