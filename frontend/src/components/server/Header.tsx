// Add 'use client' to enable hooks
'use client'

import { HomeIcon, File, UsersRound, BookOpen } from 'lucide-react';
import Link from 'next/link';
import { NavButton } from '@/components/server/NavButton';
import { ModeToggle } from '@/components/client/ModeToggle';
import { usePathname } from 'next/navigation';

export function Header() {
    const pathname = usePathname();
    return (
        <header className="animate-slide bg-background h-12 p-2 border-b sticky top-0 z-20">
            <div className="flex h-8 items-center justify-between w-full">
                <div className="flex items-center gap-2">
                    <NavButton href="/" label="Home" icon={HomeIcon} active={pathname === '/'} />
                    <Link href="/" className="flex justify-center items-center gap-2 ml-0" title="Home">
                        <h1 className="hidden sm:block text-xl font-bold m-0 mt-1">
                            AI Tutor
                        </h1>
                    </Link>
                </div>
                <div className="flex items-center">
                    <NavButton href="/learner" label="Docs" icon={UsersRound} active={pathname.startsWith('/learner')} />
                    <NavButton href="/programs" label="Learners" icon={BookOpen} active={pathname.startsWith('/programs')} />
                    <ModeToggle />
                </div>            
            </div>
        </header>
    )
}