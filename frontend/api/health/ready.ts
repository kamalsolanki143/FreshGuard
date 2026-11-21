import { handleProxy } from "../[...path]";

export default async function readyHandler(req: any, res: any) {
  return handleProxy(req, res, "/health/ready");
}
