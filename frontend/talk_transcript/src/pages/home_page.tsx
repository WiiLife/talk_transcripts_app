import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { NavigationMenu, NavigationMenuList, NavigationMenuItem, NavigationMenuContent, NavigationMenuTrigger, NavigationMenuLink } from "@/components/ui/navigation-menu"
import { Select, SelectTrigger, SelectContent, SelectGroup, SelectValue, SelectItem, SelectLabel } from "@/components/ui/select"

const HomePage = () => {
    const [modelSelected, setModelSelected] = useState("")
    const [request, setRequest] = useState(Request)

    const ExpandTextArea = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        const element = event.currentTarget
        element.style.height = "auto"
        element.style.height = (element.scrollHeight + 2) + "px"
    }

    const HandleModelSelection = () => {

    }

    const HandleRequest = () => {
        
    }

    return (
        <>
        <div className="flex w-screen justify-center">
            <NavigationMenu viewport={false} className="hidden md:block">   {/* below 768px of width it acts off */}
                <NavigationMenuList className="m-2">
                    <NavigationMenuItem>
                        <NavigationMenuTrigger>Home</NavigationMenuTrigger>
                        <NavigationMenuContent>
                            <NavigationMenuLink>
                                <a href="/">home content</a>
                            </NavigationMenuLink>
                        </NavigationMenuContent>
                    </NavigationMenuItem>
                    
                    <NavigationMenuItem>
                        <NavigationMenuTrigger>Home 1</NavigationMenuTrigger>
                        <NavigationMenuContent>
                            <NavigationMenuLink>
                                <a href="/">home content 1</a>
                            </NavigationMenuLink>
                        </NavigationMenuContent>
                    </NavigationMenuItem>

                    <NavigationMenuItem>
                        <NavigationMenuTrigger>Home 2</NavigationMenuTrigger>
                        <NavigationMenuContent>
                            <NavigationMenuLink>
                                <a href="/">home content 2</a>
                            </NavigationMenuLink>
                        </NavigationMenuContent>
                    </NavigationMenuItem>
                </NavigationMenuList>
            </NavigationMenu>
        </div>

        {/* Here I will have the model reponse being created and the prompt section moves down to the footer and becomes sticky */}

        <div className="h-screen flex items-center justify-center">
            <Card className="w-4/5">
                <CardContent className="flex">
                    <Select onOpenChange={HandleModelSelection}>
                        <SelectTrigger>
                            <SelectValue placeholder="choose model"/>
                        </SelectTrigger>
                        <SelectContent>
                            <SelectGroup>
                                <SelectLabel>Popular Models</SelectLabel>
                                <SelectItem value="mistral_small_3.2_24b">Mistral Small 3.2 24B</SelectItem>
                                <SelectItem value="gpt_oss_20b">gpt-oss-20b</SelectItem>
                                <SelectItem value="llama_3.3_8b_instruct">Llama 3.3 8B Instruct</SelectItem>
                            </SelectGroup>

                            <SelectGroup>
                                <SelectLabel>High Context Models</SelectLabel>
                                <SelectItem value="sonoma_sky_alpha">Sonoma Sky Alpha</SelectItem>
                                <SelectItem value="sonoma_dusk_alpha">Sonoma Dusk Alpha</SelectItem>
                                <SelectItem value="qwen3_coder_480b">Qwen3 Coder 480B A35B</SelectItem>
                            </SelectGroup>

                            <SelectGroup>
                                <SelectLabel>Low Latency Models</SelectLabel>
                                <SelectItem value="llama_4_maverick">Llama 4 Maverick</SelectItem>
                                <SelectItem value="qwen3_4b">Qwen3 4B</SelectItem>
                                <SelectItem value="mistral_7b_instruct">Mistral 7B Instruct</SelectItem>
                            </SelectGroup>
                        </SelectContent>
                    </Select>
                </CardContent>

                <CardContent>
                    <textarea placeholder="input a query ..." 
                              className="w-full focus:outline-none resize-none pl-1" 
                              onChange={ExpandTextArea}></textarea> 
                </CardContent>
                <CardContent className="flex justify-center">
                    <Button onClick={HandleRequest}>🡡</Button>
                </CardContent>
            </Card>
        </div>
        </>
    )
}

export default HomePage