import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, X, Star, Zap } from "lucide-react";
import Image from "next/image";
import { Assistant } from "@/lib/assistant-data";

interface AssistantListProps {
  assistants: Assistant[];
}

const AssistantList = ({ assistants }: AssistantListProps) => {
  const [selectedAssistant, setSelectedAssistant] = useState<Assistant | null>(null);

  return (
    <div className="w-full h-full font-sans">
      <motion.div
        layout
        className="w-full h-full overflow-hidden rounded-2xl bg-background text-foreground shadow-lg border border-border/20"
        initial={{
          height: "100%",
          width: "100%",
        }}
        animate={{
          height: "100%",
          width: "100%",
        }}
        transition={{ duration: 0.5, ease: "easeInOut" }}
      >
        <AnimatePresence mode="wait">
          {!selectedAssistant ? (
            <motion.div
              key="list"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="h-full flex flex-col"
            >
              <h2 className="pl-6 pt-6 text-2xl font-semibold text-foreground">AI Workers</h2>
              <p className="pl-6 pb-4 text-sm text-muted-foreground">Select a worker to view detailed information</p>

              <div className="space-y-3 p-4 flex-1 overflow-y-auto">
                {assistants.map((assistant) => (
                  <motion.div
                    key={assistant.id}
                    layoutId={`assistant-${assistant.id}`}
                    className="flex cursor-pointer items-center justify-between rounded-lg p-4 hover:bg-accent transition-colors"
                    onClick={() => setSelectedAssistant(assistant)}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <div className="flex items-center space-x-4">
                      <motion.div
                        layoutId={`avatar-${assistant.id}`}
                        className="relative w-16 h-16 rounded-full overflow-hidden bg-muted flex-shrink-0"
                        transition={{ duration: 0.5 }}
                      >
                        <Image
                          src={assistant.imagePath}
                          alt={assistant.name}
                          fill
                          className="object-cover"
                        />
                      </motion.div>
                      <div className="flex-1 min-w-0">
                        <motion.p
                          layoutId={`name-${assistant.id}`}
                          className="font-semibold text-foreground truncate text-lg"
                        >
                          {assistant.name}
                        </motion.p>
                        <motion.p
                          layoutId={`title-${assistant.id}`}
                          className="text-sm text-muted-foreground truncate"
                        >
                          {assistant.title}
                        </motion.p>
                      </div>
                    </div>
                    <motion.div
                      className="flex items-center space-x-2 text-muted-foreground"
                    >
                      <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                      <ArrowRight className="w-4 h-4" />
                    </motion.div>
                  </motion.div>
                ))}
              </div>

              {/* <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="m-auto mt-6 mb-6 flex w-11/12 items-center justify-center rounded-xl bg-primary text-primary-foreground py-3 px-6 text-base font-medium"
              >
                View All Assistants <ArrowRight className="ml-2 h-4 w-4" />
              </motion.button> */}
            </motion.div>
          ) : (
            <motion.div
              key="details"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="p-6 h-full flex flex-col"
            >
              <div className="mb-6 flex items-center justify-between">
                <motion.div
                  layoutId={`assistant-${selectedAssistant.id}`}
                  className="flex items-center space-x-4"
                >
                  <motion.div
                    layoutId={`avatar-${selectedAssistant.id}`}
                    className="relative w-20 h-20 rounded-xl overflow-hidden bg-muted"
                    transition={{ duration: 0.5 }}
                  >
                    <Image
                      src={selectedAssistant.imagePath}
                      alt={selectedAssistant.name}
                      fill
                      className="object-cover"
                    />
                  </motion.div>
                </motion.div>
                <button
                  onClick={() => setSelectedAssistant(null)}
                  className="p-3 hover:bg-muted rounded-full transition-colors"
                >
                  <X className="h-6 w-6 text-muted-foreground" />
                </button>
              </div>

              <div className="flex justify-between border-b border-border border-dashed pb-6">
                <div className="space-y-2">
                  <motion.h3
                    layoutId={`name-${selectedAssistant.id}`}
                    className="text-2xl font-bold text-foreground"
                  >
                    {selectedAssistant.name}
                  </motion.h3>
                  <motion.p
                    layoutId={`title-${selectedAssistant.id}`}
                    className="text-base text-muted-foreground"
                  >
                    {selectedAssistant.title}
                  </motion.p>
                </div>
                <div className="flex items-center space-x-2">
                  <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                  <Zap className="w-5 h-5 text-blue-500" />
                </div>
              </div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="space-y-6 flex-1 overflow-y-auto mt-6"
              >
                {/* Description */}
                <div>
                  <h4 className="font-semibold text-foreground mb-3 text-lg">Description</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {selectedAssistant.description}
                  </p>
                </div>

                {/* Skills */}
                <div>
                  <h4 className="font-semibold text-foreground mb-3 text-lg">Skills</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedAssistant.skills.map((skill, index) => (
                      <span
                        key={index}
                        className="px-3 py-1.5 bg-primary/10 text-primary text-sm rounded-full font-medium"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

export default AssistantList; 