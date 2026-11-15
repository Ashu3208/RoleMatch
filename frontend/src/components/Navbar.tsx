import { Link, NavLink } from 'react-router-dom'

type NavbarProps = {
  isSignedIn: boolean
}

export function Navbar({ isSignedIn }: NavbarProps) {
  return (
    <header className="site-header">
      <nav className="navbar" aria-label="Main navigation">
        <Link className="brand" to="/">RoleMatch</Link>
        <div className="nav-links">
          <NavLink className="nav-link" to="/" end>
            {isSignedIn ? 'Account' : 'Sign in'}
          </NavLink>
          <NavLink className="nav-link" to="/profile">Profile</NavLink>
        </div>
      </nav>
    </header>
  )
}
