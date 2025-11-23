import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle, 
  CardDescription, 
  CardAction
 } from "@/components/ui/card"
 import { Input } from "@/components/ui/input"

import { HandleMessages } from "@/components/handle_messages"
import { outputFormat } from "@/assets/outputFormat.ts"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Menu, Upload } from "lucide-react"

const backend_url: string = import.meta.env.VITE_BACKEND_URL || "localhost:8000"
const default_model: string = import.meta.env.VITE_DEFAULT_LLM_MODEL || "meta-llama/llama-3.3-8b-instruct:free"
const default_model_name: string = import.meta.env.VITE_DEFAULT_LLM_MODEL_NAME || "Llama 3.3 8B Instruct"
const maxRetries: number = import.meta.env.VITE_MAX_REQUEST_RETRIES || 3

const HomePage = () => {
  const [selectedModel, setSelectedModel] = useState<string>("")
  const [textAreaValue, setTextAreaValue] = useState<string>("")
  const [allMessages, setAllMessages] = useState<Array<unknown>>([])
  const [llmResponse, setLLMResponse] = useState<string>("")
  const [userMessage, setUserMessage] = useState<string>("")
  const [streaming, setStreaming] = useState<boolean>(false)
  const [requestLoading, setRequestLoading] = useState<boolean>(false)
  const [firstSend, setFirstSend] = useState<boolean>(true)
  const [messageCounter, setMessageCounter] = useState<number>(0)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isConnectDbOpen, setIsConnectDbOpen] = useState<boolean>(false)
  const [dbConnectionString, setDbConnectionString] = useState<string>("")

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
    setMessageCounter(prev => prev + 1)
    setTextAreaValue("")
    setLLMResponse("")
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

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // Check file type - accept both PDF and TXT
      const isValidType = file.type === 'application/pdf' || 
                         file.type === 'text/plain' ||
                         file.name.toLowerCase().endsWith('.pdf') ||
                         file.name.toLowerCase().endsWith('.txt')
      
      if (isValidType) {
        setUploadedFile(file)
        
        try {
          const formData = new FormData()
          formData.append('files', file) // Note: backend might need to handle both file types
          
          // Send to backend
          const response = await fetch(`http://${backend_url}/api/upload`, {
            method: 'POST',
            body: formData,
            // Note: Don't set Content-Type header - let browser set it with boundary
          })
          
          if (response.ok) {
            const result = await response.json()
            console.log('Upload successful:', result)
            const fileType = file.name.toLowerCase().endsWith('.pdf') ? 'PDF' : 'TXT'
            alert(`${fileType} uploaded and processed successfully!`)
          } else {
            const error = await response.text()
            console.error('Upload failed:', error)
            alert(`Failed to upload file. ${error}`)
          }
        } catch (error) {
          console.error('Upload error:', error)
          alert('Error uploading file. Please check your connection.')
        }
        
        // Clear the input so the same file can be selected again
        event.target.value = ''
      } else {
        alert('Please select a valid PDF or TXT file')
        // Clear input even on validation failure
        event.target.value = ''
      }
    }
  }

  const HandleDBConnection = async () => {

    if (!dbConnectionString.trim()) {
      alert("please enter a db connection string")
      return
    } 
    alert(`Connecting to: ${dbConnectionString} (UPCOMING FEATURE)`)
  }

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
      <div className="flex items-center justify-between border-b relative z-50 px-4 py-2">
        {/* Project Title - Home Button */}
        <button 
          onClick={() => window.location.href = '/'}
          className="text-xl font-bold hover:text-primary transition-colors"
        >
          Talk Transcripts
        </button>
        
        {/* Desktop Navigation */}
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
        
        {/* Connect DB Section */}
        <Dialog open={isConnectDbOpen} onOpenChange={setIsConnectDbOpen}>
          <DialogTrigger asChild>
            <Button>
              Connect DB
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Connect to Database</DialogTitle>
              <DialogDescription>
                Configure your database connection settings here
              </DialogDescription>
            </DialogHeader>

              {/* DB Connection string */}
              <Card>
                <CardHeader>
                  <CardTitle>Connect DB</CardTitle>
                  <CardDescription>
                    Connection your database to the LLM
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-2">
                    <Input
                      id="db-connection-string"
                      type="text"
                      placeholder="Enter db connection string"
                      value={dbConnectionString}
                      onChange={(e) => setDbConnectionString(e.target.value)}
                      className="w-full"
                    />
                    <Button onClick={HandleDBConnection}>
                      Connect
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <div className="flex justify-evenly gap-4 py-4">
                {/* PDF upload card */}
                <Card className="flex-1 min-w-0">
                  <CardHeader>
                    <CardTitle>Upload PDF</CardTitle>
                    <CardDescription>
                      Upload and process PDF files directly
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="hidden md:flex items-center">
                      <label 
                        htmlFor="nav-pdf-upload" 
                        className="flex items-center px-3 py-2 bg-primary text-primary-foreground rounded-md cursor-pointer hover:bg-primary/90 transition-colors text-sm font-medium"
                      >
                        <Upload className="w-4 h-4 mr-2" />
                        Upload PDF
                      </label>
                      <input
                        id="nav-pdf-upload"
                        type="file"
                        accept=".pdf"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* txt file upload card */}
                <Card className="flex-1 min-w-0">
                  <CardHeader>
                    <CardTitle>Upload txt file</CardTitle>
                    <CardDescription>
                      Upload and process txt files directly
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="hidden md:flex items-center">
                        <label 
                          htmlFor="nav-txt-upload" 
                          className="flex items-center px-3 py-2 bg-primary text-primary-foreground rounded-md cursor-pointer hover:bg-primary/90 transition-colors text-sm font-medium"
                        >
                          <Upload className="w-4 h-4 mr-2" />
                          Upload txt
                        </label>
                        <input
                          id="nav-txt-upload"
                          type="file"
                          accept=".txt"
                          onChange={handleFileUpload}
                          className="hidden"
                        />
                      </div>
                  </CardContent>
                </Card>
              </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsConnectDbOpen(false)}>
                Cancel
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* Mobile Menu Button */}
        <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
          <SheetTrigger asChild className="md:hidden">
            <Button variant="ghost" size="icon">
              <Menu className="h-6 w-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-[300px]">
            <div className="flex flex-col gap-4 mt-8">
              
              <label 
                htmlFor="mobile-nav-pdf-upload" 
                className="flex items-center p-2 hover:bg-accent rounded-md cursor-pointer transition-colors"
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload PDF
              </label>
              <input
                id="mobile-nav-pdf-upload"
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>
          </SheetContent>
        </Sheet>
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
          messageCounter={messageCounter}
        />
      </div>

      {/* Fixed Input Footer */}
      <div className={`sticky bottom-0 bg-background py-3 px-6 flex justify-center items-center ${firstSend ? "h-full" : ""}`}id="promptArea">
        <Card className="w-full max-w-4xl">
          <CardContent className="flex justify-between gap-2">
            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger>
                <SelectValue placeholder={firstSend ? "choose model" : default_model_name} />
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
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (textAreaValue.trim() && !requestLoading) {
                    HandleRequest();
                  }
                }
              }}
            ></textarea>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default HomePage
