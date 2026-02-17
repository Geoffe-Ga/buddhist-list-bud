import './LandingPage.css'

interface LandingPageProps {
  onEnter: () => void
}

export default function LandingPage({ onEnter }: LandingPageProps) {
  return (
    <div className="landing">
      <div className="landing-glow" />

      <div className="landing-content">
        <img
          src="/dharmaficial-intelligence.png"
          alt="Dharma-ficial Intelligence — Robot Buddha"
          className="landing-hero"
        />

        <h1 className="landing-title">Buddhist Dharma Navigator</h1>
        <p className="landing-subtitle">A product of Dharma-ficial Intelligence</p>

        <div className="landing-body">
          <p>
            In Buddhism, the <strong>Three Jewels</strong> are the foundations of practice:
            the <em>Buddha</em> (the awakened one), the <em>Dharma</em> (the teachings),
            and the <em>Sangha</em> (the community).
          </p>
          <p>
            This site is a navigator for the <strong>Dharma</strong> — the
            interconnected web of Theravada Buddhist teachings. Starting from the
            Four Noble Truths, explore how each teaching unfolds into deeper
            layers of wisdom, from the Noble Eightfold Path down to the subtlest
            factors of meditation.
          </p>
        </div>

        <button className="landing-enter" onClick={onEnter}>
          Explore the Dharma
        </button>

        <p className="landing-note">
          Site content created by AI &middot; 22 lists &middot; 118 teachings
        </p>
      </div>
    </div>
  )
}
