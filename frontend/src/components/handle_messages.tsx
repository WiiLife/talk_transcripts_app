import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';


interface Message {
  type: "user" | "system";
  content: string;
}

interface HandleMessagesProps {
  streamedResponse: string;
  userMessage: string;
  streaming: boolean;
}

export const HandleMessages: React.FC<HandleMessagesProps> = ({
  streamedResponse,
  userMessage,
  streaming,
}) => {
  const [conversation, setConversation] = useState<Message[]>([]);
  const [displayStream, setDisplayStream] = useState("");
  const prevStreamingState = useRef(streaming);
  const prevStreamedResponseRef = useRef(streamedResponse);

  useEffect(() => {
    if (userMessage.trim() !== "") {
      setConversation((prev) => [
        ...prev,
        { type: "user", content: userMessage },
      ]);
    }
  }, [userMessage]);

  useEffect(() => {
    if (prevStreamingState.current === true && streaming === false) {
      setConversation((prev) => [
        ...prev,
        { type: "system", content: streamedResponse },
      ]);
    }

    prevStreamingState.current = streaming;
  }, [streaming, streamedResponse]);

  useEffect(() => {
    if (streaming && streamedResponse !== prevStreamedResponseRef.current) {
      setDisplayStream(streamedResponse);
      prevStreamedResponseRef.current = streamedResponse;
    }

    if (!streaming) {
      setDisplayStream("");
      prevStreamedResponseRef.current = streamedResponse;
    }
  }, [streaming, streamedResponse]);

  return (
    <>
        <div className="w-full max-w-sm sm:max-w-md md:max-w-lg lg:max-w-4xl mx-auto px-4">
          <div>
            {conversation.map((item, index) => (
                <div key={index} className={`flex ${item.type === "user" ? "justify-end ml-12" : "justify-start mr-12"}`}>
                  <div className={`message-bubble ${item.type === "user" ? "bg-gray-400" : "bg-gray-200"} p-2 mt-10 rounded-lg break-words whitespace-normal`}>
                    <div className="break-words whitespace-pre-wrap">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          table: ({ children }) => (
                            <div className="overflow-x-auto w-full my-4">
                              <table className="min-w-full border-collapse border border-gray-300 text-sm">
                                {children}
                              </table>
                            </div>
                          ),
                          thead: ({ children }) => (
                            <thead className="bg-gray-50">
                              {children}
                            </thead>
                          ),
                          tbody: ({ children }) => (
                            <tbody className="divide-y divide-gray-200">
                              {children}
                            </tbody>
                          ),
                          tr: ({ children }) => (
                            <tr className="hover:bg-gray-50">
                              {children}
                            </tr>
                          ),
                          th: ({ children }) => (
                            <th className="border border-gray-300 px-3 py-2 text-left font-semibold text-gray-900 break-words whitespace-pre-wrap">
                              {children}
                            </th>
                          ),
                          td: ({ children }) => (
                            <td className="border border-gray-300 px-3 py-2 text-gray-700 break-words whitespace-pre-wrap">
                              {children}
                            </td>
                          ),
                          pre: ({ children }) => (
                            <pre className="overflow-x-auto whitespace-pre-wrap break-words bg-gray-100 p-2 rounded my-2">{children}</pre>
                          ),
                          code: ({ children }) => (
                            <code className="bg-gray-100 px-1 py-0.5 rounded text-sm break-words whitespace-pre-wrap">{children}</code>
                          ),
                          p: ({ children }) => <p className="break-words whitespace-pre-wrap mb-2">{children}</p>,
                          li: ({ children }) => <li className="break-words whitespace-pre-wrap mb-1">{children}</li>,
                          h1: ({ children }) => <h1 className="text-xl font-bold mb-2 break-words whitespace-pre-wrap">{children}</h1>,
                          h2: ({ children }) => <h2 className="text-lg font-semibold mb-2 break-words whitespace-pre-wrap">{children}</h2>,
                          h3: ({ children }) => <h3 className="text-base font-medium mb-2 break-words whitespace-pre-wrap">{children}</h3>,
                        }}
                      >    
                        {item.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
            ))}
            </div>
            
            <div>
            {streaming && (
              <div className="flex justify-start mr-12">
                <div className="message-bubble bg-gray-200 p-2 mt-10 rounded-lg break-words whitespace-normal">
                <div className="break-words whitespace-pre-wrap">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          table: ({ children }) => (
                            <div className="overflow-x-auto w-full my-4">
                              <table className="min-w-full border-collapse border border-gray-300 text-sm">
                                {children}
                              </table>
                            </div>
                          ),
                          thead: ({ children }) => (
                            <thead className="bg-gray-50">
                              {children}
                            </thead>
                          ),
                          tbody: ({ children }) => (
                            <tbody className="divide-y divide-gray-200">
                              {children}
                            </tbody>
                          ),
                          tr: ({ children }) => (
                            <tr className="hover:bg-gray-50">
                              {children}
                            </tr>
                          ),
                          th: ({ children }) => (
                            <th className="border border-gray-300 px-3 py-2 text-left font-semibold text-gray-900 break-words whitespace-pre-wrap">
                              {children}
                            </th>
                          ),
                          td: ({ children }) => (
                            <td className="border border-gray-300 px-3 py-2 text-gray-700 break-words whitespace-pre-wrap">
                              {children}
                            </td>
                          ),
                          pre: ({ children }) => (
                            <pre className="overflow-x-auto whitespace-pre-wrap break-words bg-gray-100 p-2 rounded my-2">{children}</pre>
                          ),
                          code: ({ children }) => (
                            <code className="bg-gray-100 px-1 py-0.5 rounded text-sm break-words whitespace-pre-wrap">{children}</code>
                          ),
                          p: ({ children }) => <p className="break-words whitespace-pre-wrap mb-2">{children}</p>,
                          li: ({ children }) => <li className="break-words whitespace-pre-wrap mb-1">{children}</li>,
                          h1: ({ children }) => <h1 className="text-xl font-bold mb-2 break-words whitespace-pre-wrap">{children}</h1>,
                          h2: ({ children }) => <h2 className="text-lg font-semibold mb-2 break-words whitespace-pre-wrap">{children}</h2>,
                          h3: ({ children }) => <h3 className="text-base font-medium mb-2 break-words whitespace-pre-wrap">{children}</h3>,
                        }}
                      >    
                        {displayStream}
                      </ReactMarkdown>
                    </div>
                </div>
              </div>
            )}
            </div>
        </div>      
    </>
  );
};
