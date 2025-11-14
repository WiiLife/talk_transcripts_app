import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  NavigationMenu,
  NavigationMenuList,
  NavigationMenuItem,
  NavigationMenuContent,
  NavigationMenuTrigger,
  NavigationMenuLink
} from "@/components/ui/navigation-menu"
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectGroup,
  SelectValue,
  SelectItem,
  SelectLabel
} from "@/components/ui/select"

import { HandleMessages } from "@/components/handle_messages"
import { outputFormat } from "@/assets/outputFormat.ts"

const backend_url: string = import.meta.env.VITE_BACKEND_URL   
const default_model: string = import.meta.env.VITE_DEFAULT_LLM_MODEL
const maxRetries: number = import.meta.env.VITE_MAX_REQUEST_RETRIES

const HomePage = () => {
  const [selectedModel, setSelectedModel] = useState<string>("")
  const [textAreaValue, setTextAreaValue] = useState<string>("")
  const [allMessages, setAllMessages] = useState<Array<unknown>>([])
  const [llmResponse, setLLMResponse] = useState<string>("")
  const [userMessage, setUserMessage] = useState<string>("")
  const [streaming, setStreaming] = useState<boolean>(false)
  const [requestLoading, setRequestLoading] = useState<boolean>(false)
  const [firstSend, setFirstSend] = useState<boolean>(true)

  const abortControllerRef = useRef<AbortController | null>(null);
  const chatAreaRef = useRef<HTMLDivElement | null>(null);
  const autoScrollRef = useRef(true);
  const textAutoScrollRef = useRef(true);

  const ExpandTextArea = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    const element = event.currentTarget
    element.style.height = "auto"
    if (element.scrollHeight < 200) {
        element.style.height = (element.scrollHeight + 2) + "px"
    } else {
        element.style.height = "200px";
    }

    if (textAutoScrollRef.current) {
        element.scrollTop = element.scrollHeight;
    }

    setTextAreaValue(element.value)
  }

  const HandleRequest = async () => {
    abortControllerRef.current = new AbortController();
    setUserMessage(textAreaValue)
    setTextAreaValue("")
    setFirstSend(false)

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        setRequestLoading(true);
        
        const response = await fetch(`http://${backend_url}/api/v1/chat/completions`, {
          method: "POST", 
          signal: abortControllerRef.current.signal,
          headers: {
            "Content-Type": "application/json",
            "Authorization": "none"
          }, 
          body: JSON.stringify({
            "messages": [
              ...allMessages,
              {"role": "system", "content": outputFormat},
              {"role": "user", "content": textAreaValue},
              {"role": "assistant", "content": ""}  // give the conext from the vector db with vector closest to query
            ],
            "model": selectedModel || default_model
          })
        });

        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let result = "";

        while (true) {
          setStreaming(true)
          const { done, value } = await reader.read();
          if (done) { setStreaming(false); break }
          if (value) {
            const chunk = decoder.decode(value, { stream: true });
            if (chunk.includes("Error:") || chunk.includes("ERROR:")) {
              throw new Error(`Stream error: ${chunk}`);
            }
            result += chunk;
            setLLMResponse(result);
          }
        }

        if (!result.trim()) throw new Error("Empty response");

        setAllMessages(prev => [
          ...prev, 
          {"role": "user", "content": textAreaValue},
          {"role": "assistant", "content": result}
        ]);
        
        setRequestLoading(false);
        return;
      } catch (error) {
        console.error(`Attempt ${attempt + 1} failed:`, error);
        
        if (error instanceof Error && error.name === 'AbortError') {
          setRequestLoading(false);
          break;
        }

        if (attempt < maxRetries - 1) {
          const delay = Math.pow(2, attempt) * 1000;
          await new Promise(resolve => setTimeout(resolve, delay));
        } else {
          setRequestLoading(false);
          setLLMResponse("All retries failed");
        }
      }
    }
  };

  const cancelRequest = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setRequestLoading(false);
      setStreaming(false)
    }
  };

  useEffect(() => {
    const chatArea = chatAreaRef.current;
    if (!chatArea) return;

    const handleScroll = () => {
      const nearBottom =
        chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight < 80;
      autoScrollRef.current = nearBottom;
    };

    chatArea.addEventListener("scroll", handleScroll);
    return () => chatArea.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (streaming && autoScrollRef.current && chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
    }
  }, [llmResponse, userMessage, streaming]);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background text-foreground">
      {/* Navigation */}
      <div className="flex justify-center border-b">
        <NavigationMenu viewport={false} className="hidden md:block">
          <NavigationMenuList className="m-2">
            <NavigationMenuItem>
              <NavigationMenuTrigger>Home</NavigationMenuTrigger>
              <NavigationMenuContent>
                <NavigationMenuLink href="/">
                  <p>home content</p>
                </NavigationMenuLink>
              </NavigationMenuContent>
            </NavigationMenuItem>
          </NavigationMenuList>
        </NavigationMenu>
      </div>

      {/* Scrollable Chat Area */}
      <div
        ref={chatAreaRef}
        className={`${firstSend ? "flex" : "flex-1"} overflow-y-auto px-6 py-4 scroll-smooth p-80 justify-items-center`}
        id="chatArea"
      >
        <HandleMessages
          streamedResponse={llmResponse}
          userMessage={userMessage}
          streaming={streaming}
        />
      </div>

      {/* Fixed Input Footer */}
      <div className={`sticky bottom-0 bg-background py-3 px-6 flex justify-center items-center ${firstSend ? "h-full" : ""}`}id="promptArea">
        <Card className="w-full max-w-4xl">
          <CardContent className="flex justify-between gap-2">
            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger>
                <SelectValue placeholder="choose model" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectLabel>Popular Models</SelectLabel>
                  <SelectItem value="mistralai/mistral-small-3.2-24b-instruct:free">Mistral Small 3.2 24B</SelectItem>
                  <SelectItem value="openai/gpt-oss-20b:free">gpt-oss-20b</SelectItem>
                  <SelectItem value="meta-llama/llama-3.3-8b-instruct:free">Llama 3.3 8B Instruct</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>

            <Button
              onClick={requestLoading ? cancelRequest : HandleRequest}
              disabled={!textAreaValue.trim() && !streaming}
            >
              {requestLoading ? "X" : "🡡"}
            </Button>
          </CardContent>

          <CardContent>
            <textarea
              placeholder="input a query ..."
              id="textArea"
              className="w-full focus:outline-none resize-none pl-1"
              onChange={ExpandTextArea}
              value={textAreaValue}
              rows={1}
            ></textarea>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default HomePage
