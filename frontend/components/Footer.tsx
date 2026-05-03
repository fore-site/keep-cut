import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-[#e2e1de] py-6 mt-12">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-gray-500">
          <div className="flex gap-4">
            <Link 
              href="/" 
              className="hover:text-terracotta transition-colors"
            >
              Home
            </Link>
            <a 
              href="https://github.com/fore-site/keep-cut" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-terracotta transition-colors"
            >
              GitHub
            </a>
              <a
                href="https://x.com/fore_site"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-terracotta transition-colors"
              >
                Contact developer
              </a>
          </div>
          <p className="text-xs text-center">
            © {new Date().getFullYear()} Keep-Cut Game. Data from{" "}
            <a 
              href="https://www.themoviedb.org/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-terracotta transition-colors"
            >
              TMDB
            </a>{" "}
            and{" "}
            <a 
              href="https://anilist.co/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-terracotta transition-colors"
            >
              AniList
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}