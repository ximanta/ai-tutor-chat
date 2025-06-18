import { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import Link from "next/link";

// Add 'active' prop to Props
type Props = {
    icon: LucideIcon,
    label: string,
    href?: string,
    active?: boolean,
}

export function NavButton({
    icon: Icon,
    label,
    href,
    active = false,
}: Props) {
    return (
        <Button
            variant={active ? 'secondary' : 'ghost'}
            size="icon"
            aria-label={label}
            title={label}
            className={active ? 'rounded-full border border-primary' : 'rounded-full'}
            asChild
        >
            {href ? (
                <Link href={href}>
                    <Icon />
                </Link>
            ) : (
                <Icon />
            )}
        </Button>
    )
}