import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

const HomePage = () => {
    return (
        <div className="h-screen flex items-center justify-center">
            <Input type="query" placeholder="query here"></Input>
            <Button>send</Button>
        </div>
    )
}

export default HomePage