// cytoscape-elk ships no types; it's a Cytoscape layout extension registered via cytoscape.use().
declare module "cytoscape-elk" {
  import type { Ext } from "cytoscape";

  const elk: Ext;
  export default elk;
}
