import type { ReactNode } from "react";
import clsx from "clsx";
import Link from "@docusaurus/Link";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Layout from "@theme/Layout";
import Heading from "@theme/Heading";

import styles from "./index.module.css";

function HomepageHeader() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <header className={clsx("hero hero--primary", styles.heroBanner)}>
      <div className={styles.stars} id="stars"></div>
      <div className="container">
        <div className={styles.header}>
          <div className={styles.logo}>🛸</div>
          <Heading as="h1" className={clsx("hero__title", styles.title)}>
            Starmates
          </Heading>
          <p className={clsx("hero__subtitle", styles.welcomeText)}>
            Welcome aboard, Captain. Your AI crew awaits.
          </p>
          <p className={styles.description}>
            Use natural language to automate your universe.
          </p>
          <div className={styles.buttons}>
            <Link
              className={clsx(
                "button button--primary button--lg",
                styles.exploreButton
              )}
              to="/docs"
            >
              Explore Captain's Working Documents
              <span>📋</span>
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title}`}
      description="Welcome aboard, Captain. Your AI crew awaits."
    >
      <HomepageHeader />
    </Layout>
  );
}
