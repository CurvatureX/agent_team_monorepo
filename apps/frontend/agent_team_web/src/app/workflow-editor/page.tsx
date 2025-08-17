// "use client";

// import React, { useCallback } from 'react';
// import { Provider } from 'jotai';
// import { WorkflowEditor } from '@/components/workflow/WorkflowEditor';
// import { Button } from '@/components/ui/button';
// import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
// import { Textarea } from '@/components/ui/textarea';
// import { Save, Eye, Copy, Check } from 'lucide-react';
// import { useToast } from '@/hooks/use-toast';
// import { useWorkflow } from '@/store/hooks';

// // Inner component that uses the hooks (must be inside Provider)
// function WorkflowEditorWithToolbar() {
//   const { toast } = useToast();
//   const { nodes, edges, metadata, exportWorkflow } = useWorkflow();
//   const [showJsonDialog, setShowJsonDialog] = React.useState(false);
//   const [jsonOutput, setJsonOutput] = React.useState('');
//   const [copied, setCopied] = React.useState(false);

//   // Debug log
//   React.useEffect(() => {
//     console.log('WorkflowEditorContent mounted - Nodes:', nodes.length, 'Edges:', edges.length);
//   }, [nodes, edges]);

//   // Log changes
//   React.useEffect(() => {
//     console.log('Nodes updated in page:', nodes);
//     console.log('Nodes length:', nodes.length);
//     console.log('Nodes content:', JSON.stringify(nodes, null, 2));
//   }, [nodes]);

//   React.useEffect(() => {
//     console.log('Edges updated in page:', edges);
//     console.log('Edges length:', edges.length);
//   }, [edges]);

//   const handleSave = useCallback(() => {
//     const workflowData = exportWorkflow();
    
//     // 直接打印当前的workflow数据到控制台
//     console.log('=== Saving Workflow ===');
//     console.log('Metadata:', metadata);
//     console.log('Nodes:', nodes);
//     console.log('Edges:', edges);
//     console.log('Exported Data:', workflowData);
//     console.log('======================');
    
//     toast({
//       title: "Workflow saved",
//       description: `${nodes.length} nodes, ${edges.length} edges - Check console for details`,
//     });
//   }, [nodes, edges, metadata, exportWorkflow, toast]);

//   const handleViewJson = useCallback(() => {
//     const workflowData = {
//       metadata,
//       nodes,
//       edges
//     };

//     const formattedJson = JSON.stringify(workflowData, null, 2);
//     setJsonOutput(formattedJson);
//     setShowJsonDialog(true);
//   }, [nodes, edges, metadata]);

//   const handleCopyJson = useCallback(() => {
//     navigator.clipboard.writeText(jsonOutput);
//     setCopied(true);
//     toast({
//       title: "Copied",
//       description: "JSON has been copied to clipboard",
//     });
//     setTimeout(() => setCopied(false), 2000);
//   }, [jsonOutput, toast]);

//   return (
//     <div className="h-screen w-full flex flex-col">
//       {/* Toolbar */}
//       <div className="h-14 border-b bg-white dark:bg-gray-900 shadow-sm">
//         <div className="h-full px-4 flex items-center justify-between">
//           <div className="flex items-center gap-2">
//             <h1 className="text-lg font-semibold">Workflow Editor</h1>
//           </div>
//           <div className="flex items-center gap-2">
//             <Button
//               variant="outline"
//               size="default"
//               onClick={handleViewJson}
//               className="gap-2"
//             >
//               <Eye className="h-4 w-4" />
//               View JSON
//             </Button>
//             <Button
//               variant="default"
//               size="default"
//               onClick={handleSave}
//               className="gap-2 bg-blue-600 hover:bg-blue-700 text-white"
//             >
//               <Save className="h-4 w-4" />
//               Save Workflow
//             </Button>
//           </div>
//         </div>
//       </div>

//       {/* Editor */}
//       <div className="flex-1 relative">
//         <WorkflowEditor
//           readOnly={false}
//         />
//       </div>

//       {/* JSON Output Dialog */}
//       <Dialog open={showJsonDialog} onOpenChange={setShowJsonDialog}>
//         <DialogContent className="max-w-3xl max-h-[80vh]">
//           <DialogHeader>
//             <DialogTitle>Workflow JSON Output</DialogTitle>
//             <DialogDescription>
//               Current workflow data in JSON format
//             </DialogDescription>
//           </DialogHeader>
//           <div className="relative">
//             <div className="absolute top-2 right-2 z-10">
//               <Button
//                 variant="outline"
//                 size="sm"
//                 onClick={handleCopyJson}
//                 className="gap-2"
//               >
//                 {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
//                 {copied ? 'Copied' : 'Copy'}
//               </Button>
//             </div>
//             <Textarea
//               value={jsonOutput}
//               readOnly
//               className="font-mono text-xs h-[400px] resize-none"
//             />
//           </div>
//         </DialogContent>
//       </Dialog>
//     </div>
//   );
// }

// // Main component - wrap everything in a single Provider
// export default function WorkflowEditorPage() {
//   return (
//     <Provider>
//       <WorkflowEditorWithToolbar />
//     </Provider>
//   );
// }