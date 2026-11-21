import { handleProxy, VercelRequest, VercelResponse } from "../../_lib/proxy";

export default async function verificationByIdHandler(req: VercelRequest, res: VercelResponse) {
  const id = (req.query?.id as string) || (req.url || "").split("/").pop() || "";
  const cleanId = encodeURIComponent(id.split("?")[0]);
  return handleProxy(req, res, `/v1/verifications/${cleanId}`);
}
